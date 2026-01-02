"""
RateLimiter - Controle de taxa de requisições com backoff exponencial.

Evita:
1. Bloqueio por excesso de requisições
2. Bans permanentes de IP
3. Sobrecarga do servidor alvo
"""

import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class DomainState:
    """Estado de rate limiting para um domínio específico."""
    last_request_time: float = 0.0
    consecutive_errors: int = 0
    is_blocked: bool = False
    block_until: float = 0.0
    total_requests: int = 0
    total_errors: int = 0

class RateLimiter:
    """
    Rate limiter com backoff exponencial por domínio.
    """
    
    def __init__(
        self,
        requests_per_second: float = 1.0,
        max_consecutive_errors: int = 3,
        base_backoff: float = 5.0,
        max_backoff: float = 300.0,  # 5 minutos máximo
    ):
        """
        Args:
            requests_per_second: Máximo de requisições por segundo por domínio
            max_consecutive_errors: Erros consecutivos antes de aplicar backoff
            base_backoff: Tempo base de backoff em segundos
            max_backoff: Tempo máximo de backoff em segundos
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.max_consecutive_errors = max_consecutive_errors
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff
        
        self._domains: Dict[str, DomainState] = {}
        self._lock = asyncio.Lock()
    
    def _get_domain(self, url: str) -> str:
        """Extrai o domínio de uma URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    def _get_state(self, domain: str) -> DomainState:
        """Obtém ou cria o estado de um domínio."""
        if domain not in self._domains:
            self._domains[domain] = DomainState()
        return self._domains[domain]
    
    async def acquire(self, url: str) -> bool:
        """
        Aguarda até que seja permitido fazer uma requisição.
        
        Returns:
            True se pode prosseguir, False se o domínio está bloqueado
        """
        domain = self._get_domain(url)
        
        async with self._lock:
            state = self._get_state(domain)
            now = time.time()
            
            # Verifica se está bloqueado
            if state.is_blocked:
                if now < state.block_until:
                    remaining = state.block_until - now
                    logger.warning(f"Domain {domain} is blocked for {remaining:.1f}s more")
                    return False
                else:
                    # Desbloqueia
                    state.is_blocked = False
                    state.consecutive_errors = 0
                    logger.info(f"Domain {domain} unblocked")
            
            # Calcula tempo de espera
            time_since_last = now - state.last_request_time
            wait_time = max(0, self.min_interval - time_since_last)
            
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
                await asyncio.sleep(wait_time)
            
            # Atualiza estado
            state.last_request_time = time.time()
            state.total_requests += 1
            
            return True
    
    def record_success(self, url: str):
        """Registra uma requisição bem-sucedida."""
        domain = self._get_domain(url)
        state = self._get_state(domain)
        state.consecutive_errors = 0
    
    def record_error(self, url: str, is_rate_limit: bool = False):
        """
        Registra um erro de requisição.
        
        Args:
            url: URL que falhou
            is_rate_limit: True se o erro foi 429 (Too Many Requests)
        """
        domain = self._get_domain(url)
        state = self._get_state(domain)
        
        state.consecutive_errors += 1
        state.total_errors += 1
        
        # Aplica backoff se excedeu limite de erros
        if state.consecutive_errors >= self.max_consecutive_errors or is_rate_limit:
            # Calcula tempo de backoff exponencial
            backoff_multiplier = 2 ** (state.consecutive_errors - self.max_consecutive_errors)
            backoff_time = min(
                self.base_backoff * backoff_multiplier,
                self.max_backoff
            )
            
            if is_rate_limit:
                # Rate limit é mais severo
                backoff_time = min(backoff_time * 2, self.max_backoff)
            
            state.is_blocked = True
            state.block_until = time.time() + backoff_time
            
            logger.warning(
                f"Domain {domain} blocked for {backoff_time:.1f}s "
                f"(consecutive errors: {state.consecutive_errors})"
            )
    
    def get_stats(self, url: Optional[str] = None) -> Dict:
        """
        Retorna estatísticas de rate limiting.
        
        Args:
            url: Se fornecido, retorna stats apenas para este domínio
        """
        if url:
            domain = self._get_domain(url)
            state = self._get_state(domain)
            return {
                'domain': domain,
                'total_requests': state.total_requests,
                'total_errors': state.total_errors,
                'consecutive_errors': state.consecutive_errors,
                'is_blocked': state.is_blocked,
                'error_rate': state.total_errors / max(1, state.total_requests)
            }
        
        return {
            domain: {
                'total_requests': state.total_requests,
                'total_errors': state.total_errors,
                'error_rate': state.total_errors / max(1, state.total_requests)
            }
            for domain, state in self._domains.items()
        }
    
    def reset(self, url: Optional[str] = None):
        """
        Reseta o estado do rate limiter.
        
        Args:
            url: Se fornecido, reseta apenas este domínio
        """
        if url:
            domain = self._get_domain(url)
            if domain in self._domains:
                del self._domains[domain]
        else:
            self._domains.clear()


# Instância global para uso compartilhado
_global_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    """Obtém a instância global do rate limiter."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter

async def rate_limited_fetch(
    url: str,
    fetch_func,
    rate_limiter: Optional[RateLimiter] = None
):
    """
    Wrapper para fetch com rate limiting.
    
    Args:
        url: URL para buscar
        fetch_func: Função de fetch (síncrona ou assíncrona)
        rate_limiter: RateLimiter a usar (usa global se não fornecido)
    """
    limiter = rate_limiter or get_rate_limiter()
    
    # Aguarda permissão
    if not await limiter.acquire(url):
        raise Exception(f"Domain temporarily blocked: {url}")
    
    try:
        # Executa fetch
        if asyncio.iscoroutinefunction(fetch_func):
            result = await fetch_func(url)
        else:
            result = fetch_func(url)
        
        limiter.record_success(url)
        return result
        
    except Exception as e:
        # Detecta se é rate limit (HTTP 429)
        is_rate_limit = '429' in str(e) or 'Too Many Requests' in str(e)
        limiter.record_error(url, is_rate_limit)
        raise

