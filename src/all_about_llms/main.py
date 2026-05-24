import uvicorn

from all_about_llms.config import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "all_about_llms.app:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.environment == "local",
    )


if __name__ == "__main__":
    main()
