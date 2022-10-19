from config import SOAP_USERNAME, SOAP_PASSWORD
from soap_parser import SoapParser


def main():
    soap = SoapParser(username=SOAP_USERNAME, password=SOAP_PASSWORD)
    soap.get_shows()


if __name__ == '__main__':
    main()
