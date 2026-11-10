
"""Client Python de l'API MaintAI."""

import httpx


class APIError(Exception):
    """L'API a répondu avec un code différent de 200."""

    def __init__(self, status_code: int, detail):
        super().__init__(f"Erreur {status_code} : {detail}")
        self.status_code = status_code
        self.detail = detail


class MaintaiClient:

    def __init__(
        self,
        url: str = "http://localhost:8000",
        api_key: str | None = None,
        http: httpx.Client | None = None
    ):
        # Client HTTP
        self.http = http or httpx.Client(
            base_url=url,
            timeout=5.0
        )

        self.api_key = api_key

    def health(self) -> dict:
        """Vérifier si l'API fonctionne."""

        r = self.http.get("/health")
        r.raise_for_status()

        return r.json()

    def predict(self, reading: dict) -> dict:
        """Envoyer un relevé et récupérer la prédiction."""

        # 1. Préparer les en-têtes
        headers = {}

        if self.api_key:
            headers["X-API-Key"] = self.api_key

        # 2. Envoyer la requête POST
        r = self.http.post(
            "/v1/predict",
            json=reading,
            headers=headers
        )

        # 3. Vérifier la réponse
        if r.status_code != 200:

            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text

            raise APIError(
                r.status_code,
                detail
            )

        # 4. Retourner le résultat JSON
        return r.json()
