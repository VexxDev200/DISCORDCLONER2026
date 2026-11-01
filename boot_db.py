# Импорт драйвера БД до любых подключений (важно для PyInstaller onefile).
def boot():
    try:
        import psycopg  # noqa: F401
        try:
            import psycopg_binary  # noqa: F401
        except ImportError:
            pass
        return True
    except ImportError:
        return False


boot()
