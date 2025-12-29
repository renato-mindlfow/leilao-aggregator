import os
import httpx
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

ASAAS_API_KEY = os.environ.get('ASAAS_API_KEY')
ASAAS_BASE_URL = "https://api.asaas.com/api/v3"

class AsaasService:
    
    def __init__(self):
        self.headers = {
            "access_token": ASAAS_API_KEY,
            "Content-Type": "application/json"
        }
    
    async def create_customer(
        self, 
        user_id: str, 
        name: str, 
        email: str, 
        cpf_cnpj: Optional[str] = None,
        phone: Optional[str] = None
    ) -> dict:
        """Cria ou atualiza cliente no Asaas"""
        
        # Verificar se cliente já existe
        existing = await self._get_customer_by_email(email)
        if existing:
            return {"success": True, "customer_id": existing["id"]}
        
        payload = {
            "name": name,
            "email": email,
            "externalReference": user_id,
            "notificationDisabled": False
        }
        
        if cpf_cnpj:
            payload["cpfCnpj"] = cpf_cnpj
        if phone:
            payload["phone"] = phone
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ASAAS_BASE_URL}/customers",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return {"success": True, "customer_id": data["id"]}
            else:
                logger.error(f"Erro ao criar cliente Asaas: {response.text}")
                return {"success": False, "error": response.text}
    
    async def _get_customer_by_email(self, email: str) -> Optional[dict]:
        """Busca cliente pelo email"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ASAAS_BASE_URL}/customers",
                params={"email": email},
                headers=self.headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data") and len(data["data"]) > 0:
                    return data["data"][0]
        return None
    
    async def create_payment_link(
        self,
        user_id: str,
        user_name: str,
        user_email: str,
        plan: str = "monthly"
    ) -> dict:
        """Cria link de pagamento para checkout"""
        
        plans = {
            "monthly": {
                "name": "LeiloHub Premium - Mensal",
                "value": 89.90,
                "cycle": "MONTHLY",
                "description": "Assinatura mensal - Acesso ilimitado a todos os imóveis"
            },
            "yearly": {
                "name": "LeiloHub Premium - Anual",
                "value": 838.80,
                "cycle": "YEARLY",
                "description": "Assinatura anual (12x R$ 69,90) - Economize 22%!"
            }
        }
        
        plan_config = plans.get(plan, plans["monthly"])
        
        # Primeiro criar/obter cliente
        customer_result = await self.create_customer(user_id, user_name, user_email)
        if not customer_result["success"]:
            return customer_result
        
        customer_id = customer_result["customer_id"]
        
        # Criar assinatura
        next_due = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        payload = {
            "customer": customer_id,
            "billingType": "UNDEFINED",  # Cliente escolhe Pix ou Cartão
            "value": plan_config["value"],
            "nextDueDate": next_due,
            "cycle": plan_config["cycle"],
            "description": plan_config["description"],
            "externalReference": f"{user_id}_{plan}",
        }
        
        # Para plano anual, permitir parcelamento
        if plan == "yearly":
            payload["maxInstallmentCount"] = 12
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ASAAS_BASE_URL}/subscriptions",
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                # Asaas pode retornar invoiceUrl na resposta ou pode precisar buscar a primeira fatura
                checkout_url = data.get("invoiceUrl") or data.get("url")
                # Se não tem URL direta, tentar buscar a primeira fatura da assinatura
                if not checkout_url and data.get("id"):
                    # Criar um link temporário - na prática, o Asaas gera uma fatura automaticamente
                    # que pode ser acessada via dashboard do cliente
                    checkout_url = f"https://www.asaas.com/c/{customer_id}"
                return {
                    "success": True,
                    "subscription_id": data["id"],
                    "checkout_url": checkout_url,
                    "customer_id": customer_id
                }
            else:
                logger.error(f"Erro ao criar assinatura Asaas: {response.text}")
                return {"success": False, "error": response.text}
    
    async def cancel_subscription(self, subscription_id: str) -> dict:
        """Cancela uma assinatura"""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{ASAAS_BASE_URL}/subscriptions/{subscription_id}",
                headers=self.headers,
                timeout=30.0
            )
            return {"success": response.status_code in [200, 204]}
    
    def handle_webhook(self, payload: dict, db) -> dict:
        """Processa webhook do Asaas"""
        
        event = payload.get("event")
        payment = payload.get("payment", {})
        subscription = payload.get("subscription")
        
        logger.info(f"Webhook Asaas recebido: {event}")
        
        external_ref = payment.get("externalReference") or ""
        
        if not external_ref and subscription:
            # Tentar pegar do subscription
            external_ref = subscription if isinstance(subscription, str) else ""
        
        # Extrair user_id do externalReference (formato: user_id_plan)
        user_id = external_ref.split("_")[0] if "_" in external_ref else external_ref
        
        if not user_id:
            logger.warning("Webhook sem user_id identificável")
            return {"success": True, "action": "ignored_no_user"}
        
        # Processar eventos
        if event in ["PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"]:
            self._activate_subscription(user_id, payment, db)
            return {"success": True, "action": "subscription_activated", "user_id": user_id}
        
        elif event == "PAYMENT_OVERDUE":
            self._mark_payment_overdue(user_id, db)
            return {"success": True, "action": "marked_overdue", "user_id": user_id}
        
        elif event in ["SUBSCRIPTION_DELETED", "SUBSCRIPTION_INACTIVATED"]:
            self._cancel_user_subscription(user_id, db)
            return {"success": True, "action": "subscription_cancelled", "user_id": user_id}
        
        return {"success": True, "action": "ignored", "event": event}
    
    def _activate_subscription(self, user_id: str, payment: dict, db):
        """Ativa assinatura do usuário"""
        value = payment.get("value", 0)
        plan = "yearly" if value > 500 else "monthly"
        
        end_date = datetime.now() + timedelta(days=365 if plan == "yearly" else 30)
        
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_profiles SET
                        subscription_status = 'active',
                        subscription_plan = %s,
                        subscription_start_date = NOW(),
                        subscription_end_date = %s,
                        updated_at = NOW()
                    WHERE id = %s::uuid
                """, (plan, end_date, user_id))
            conn.commit()
        
        logger.info(f"Assinatura ativada para user {user_id}, plano {plan}")
    
    def _mark_payment_overdue(self, user_id: str, db):
        """Marca pagamento como atrasado"""
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_profiles SET
                        subscription_status = 'overdue',
                        updated_at = NOW()
                    WHERE id = %s::uuid
                """, (user_id,))
            conn.commit()
    
    def _cancel_user_subscription(self, user_id: str, db):
        """Cancela assinatura"""
        with db._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE user_profiles SET
                        subscription_status = 'cancelled',
                        asaas_subscription_id = NULL,
                        updated_at = NOW()
                    WHERE id = %s::uuid
                """, (user_id,))
            conn.commit()


# Instância global
asaas_service = AsaasService()

