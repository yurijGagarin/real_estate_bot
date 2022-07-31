import requests

import config


def main():
    r = requests.get(url=config.SPREADSHEET_URL, auth=(config.USER_EMAIL_SPR, config.PASSWORD_SPR))

    print(r.content)


if __name__ == "__main__":
    main()
