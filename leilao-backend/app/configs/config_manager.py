"""
Config Manager - Gerencia configurações de sites de leilões.
"""
import os
import json
import logging
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    """Gerencia configurações de sites de leilões."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Inicializa o ConfigManager.
        
        Args:
            config_dir: Diretório onde estão os arquivos de configuração.
                       Default: app/configs/sites/
        """
        if config_dir is None:
            # Tenta encontrar o diretório relativo ao módulo
            base_path = Path(__file__).parent.parent.parent
            config_dir = base_path / "app" / "configs" / "sites"
        else:
            config_dir = Path(config_dir)
        
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict] = {}
    
    def get_config(self, site_name: str) -> Optional[Dict[str, Any]]:
        """
        Carrega configuração de um site.
        
        Args:
            site_name: Nome do site (sem extensão .json)
        
        Returns:
            Dict com configuração ou None se não encontrado
        """
        if site_name in self._cache:
            return self._cache[site_name]
        
        config_file = self.config_dir / f"{site_name}.json"
        
        if not config_file.exists():
            logger.warning(f"Arquivo de configuração não encontrado: {config_file}")
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self._cache[site_name] = config
                return config
        except Exception as e:
            logger.error(f"Erro ao carregar configuração {site_name}: {e}")
            return None
    
    def save_config(self, site_name: str, config: Dict[str, Any]) -> bool:
        """
        Salva configuração de um site.
        
        Args:
            site_name: Nome do site (sem extensão .json)
            config: Dict com configuração
        
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        config_file = self.config_dir / f"{site_name}.json"
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self._cache[site_name] = config
            logger.info(f"Configuração salva: {config_file}")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configuração {site_name}: {e}")
            return False
    
    def list_configs(self) -> list[str]:
        """
        Lista todos os sites configurados.
        
        Returns:
            Lista de nomes de sites (sem extensão .json)
        """
        if not self.config_dir.exists():
            return []
        
        configs = []
        for file in self.config_dir.glob("*.json"):
            configs.append(file.stem)
        
        return sorted(configs)
    
    def delete_config(self, site_name: str) -> bool:
        """
        Deleta configuração de um site.
        
        Args:
            site_name: Nome do site (sem extensão .json)
        
        Returns:
            True se deletou com sucesso, False caso contrário
        """
        config_file = self.config_dir / f"{site_name}.json"
        
        if not config_file.exists():
            return False
        
        try:
            config_file.unlink()
            if site_name in self._cache:
                del self._cache[site_name]
            logger.info(f"Configuração deletada: {config_file}")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar configuração {site_name}: {e}")
            return False
