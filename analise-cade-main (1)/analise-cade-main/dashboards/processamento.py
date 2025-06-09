from diskcache import Cache
import logging
import json
import jsonschema
from typing import Dict, Any, Optional
from model_config import configure_gemini_model
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tqdm.auto import tqdm
import pandas as pd

cache = Cache("cache_processamento")

SCHEMA_JURIDICO = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "decisao_tribunal": {
            "enum": ["Condenação", "Arquivamento", None],
            "description": "Decisão final do tribunal"
        },
        "seguiu_nota_tecnica": {
            "type": ["boolean", "null"],
            "description": "Indica se seguiu nota técnica"
        },
        "tipo_infracao_concorrencial": {
            "type": ["string", "null"],
            "description": "Tipo de infração concorrencial"
        },
        "multa": {
            "type": "boolean",
            "description": "Existência de multa"
        },
        "tipo_de_multa": {
            "enum": ["valor_fixo", "percentual", "ambos", None],
            "description": "Tipo de multa aplicada"
        },
        "valor_multa_reais": {
            "type": ["number", "null"],
            "minimum": 0,
            "description": "Valor em reais da multa"
        },
        "percentual_faturamento": {
            "type": ["number", "null"],
            "minimum": 0,
            "maximum": 100,
            "description": "Percentual sobre faturamento"
        }
    },
    "required": [
        "decisao_tribunal", "seguiu_nota_tecnica", "multa",
        "tipo_de_multa", "valor_multa_reais", "percentual_faturamento"
    ],
    "additionalProperties": False,
    "dependentRequired": {
        "multa": ["tipo_de_multa"],
        "tipo_de_multa": ["valor_multa_reais", "percentual_faturamento"]
    },
    "if": {
        "properties": {"multa": {"const": False}},
        "then": {
            "properties": {
                "tipo_de_multa": {"const": None},
                "valor_multa_reais": {"const": None},
                "percentual_faturamento": {"const": None}
            }
        }
    }
}


def extrair_informacoes_juridicas(texto: str) -> Optional[Dict[str, Any]]:
    try:
        prompt = f"""
        Analise COMPLETAMENTE o documento jurídico abaixo seguindo:
        1. Identifique todos os elementos do schema
        2. Mantenha o texto integral sem divisões
        3. Retorne JSON válido mesmo para valores ausentes

        Documento:
        \"\"\"{texto}\"\"\"
        
        Formato de resposta exigido (JSON válido):
        {json.dumps(SCHEMA_JURIDICO, indent=2)}
        """
        modelo = configure_gemini_model()
        resposta = modelo.generate_content(prompt)
        json_str = resposta.text.strip().replace('``````', '')
        data = json.loads(json_str)
        
        jsonschema.validate(instance=data, schema=SCHEMA_JURIDICO)

        return data

    except Exception as e:
        logging.error(f"Erro no documento de {len(texto)} caracteres: {str(e)[:200]}...")
        return None

    
def processar_em_lote(df: pd.DataFrame, coluna_texto: str, workers: int = 5) -> pd.DataFrame:
    """Processamento paralelo otimizado para grandes volumes."""
    textos = df[coluna_texto].tolist()
    
    with ThreadPoolExecutor(max_workers=workers) as executor:
        resultados = list(tqdm(
            executor.map(extrair_informacoes_juridicas, textos),
            total=len(textos),
            desc="📄 Processando Documentos",
            bar_format='{l_bar}{bar:20}{r_bar}{bar:-20b}'
        ))
    
    # Garante todas as colunas mesmo com resultados nulos
    dados_normalizados = []
    for resultado in resultados:
        if resultado:
            dados_normalizados.append(resultado)
        else:
            dados_normalizados.append({k: None for k in SCHEMA_JURIDICO['properties']})
    
    df_resultados = pd.json_normalize(dados_normalizados).add_suffix('_ia')
    
    return pd.concat([df.reset_index(drop=True), df_resultados], axis=1)


def analisa(df):
    @cache.memoize(expire=60*60*24*7)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((json.JSONDecodeError, jsonschema.ValidationError))
    )
    def _analisa(df):
        return processar_em_lote(df, 'conteudo')
    
    df_final = _analisa(df)
    return df_final 



