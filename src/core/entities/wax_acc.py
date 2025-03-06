from dataclasses import dataclass, asdict


@dataclass
class BuyRam:
    ram_receiver_acc: str
    ram_bytes: int


@dataclass
class WaxAccount:
    wallet: str
    email: str | None
    token: str | None
    key: str | None

    def __hash__(self):
        return hash(self.wallet)

    def to_dict(self):
        return asdict(self)


def main():
    test_acc = WaxAccount(
        wallet="somewallet", email="<EMAIL>", token="<PASSWORD>", key="somekey"
    )
    log.info("test WaxAccount: %s", test_acc)


if __name__ == "__main__":
    import logging
    from settings import configure_color_logging

    log = logging.getLogger(__name__)
    configure_color_logging(level=logging.DEBUG)

    main()
