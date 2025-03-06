from enum import Enum
from .interfaces import NonceGenerator
from .implementations.external_nonce import ExternalNonce


class NonceGeneratorType(Enum):
    EXTERNAL = "external"
    LOCAL = "local"


def create_nonce_generator(generator_type: NonceGeneratorType) -> NonceGenerator:
    if generator_type == NonceGeneratorType.EXTERNAL:
        return ExternalNonce()
    # добавить другие реализации по мере необходимости
    raise ValueError(f"Unknown generator type: {generator_type}")
