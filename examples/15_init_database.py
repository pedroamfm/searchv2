from meli.database import DATABASE_PATH, connect, initialize


def main() -> None:
    connection = connect()
    try:
        initialize(connection)
        print(f"Base SQLite inicializada: {DATABASE_PATH}")
    finally:
        connection.close()


if __name__ == "__main__":
    main()
