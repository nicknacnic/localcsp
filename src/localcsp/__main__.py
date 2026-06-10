import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "localcsp.app:app",
        host=os.environ.get("LOCALCSP_HOST", "127.0.0.1"),
        port=int(os.environ.get("LOCALCSP_PORT", "8081")),
        log_level="warning",
    )


if __name__ == "__main__":
    main()
