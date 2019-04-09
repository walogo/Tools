from socket import socket, AF_INET, AF_INET6, SOCK_STREAM
from re import match
from argparse import ArgumentParser


# Printer for responses
def print_response(response):
    if response:
        print(response.decode())


# Find every file in a list like the one of "ls" command
def find_posible_file(pattern, ls_list):  # NOT IMPLEMENTED
    m = match(pattern, ls_list)


# Get command/code and args
def getCodeOrCommand(cmd):
    return cmd.split(' ')


# Handler for the FTP session
class FTPHandler:
    def __init__(self, address, client):
        self.__host, self.__port = address

        self.__client = client  # Socket for command communication
        self.__logged_in = False  # Useful handler to limit the client and prevent crash by not executing certain cmds before we are logged in
        self.__timeout = 1  # The timeout for the recv
        self.__is_active = False

    # Passive eFTP connection
    def __pasv(self):
        self.__client.send(b'PASV\r\n')
        # Receive port to connect
        cmd = self.__recv(self.__client).decode()
        # Separate the  args from the PORT command
        code, *args = getCodeOrCommand(cmd)
        # When the server have implemented it
        pre_port = args[-1].replace('(', '').replace(')', '').replace('.', '').strip().split(',')
        port = int(pre_port[4]) * 256 + int(pre_port[5])
        # Connect with the received port
        data_client = socket(AF_INET, SOCK_STREAM)
        address = ('.'.join(pre_port[:4]), port)
        data_client.connect(address)
        return data_client

    # get command from string
    def __getCommandString(self, cmd):
        try:
            return getattr(self, cmd)
        except:
            return None

    # Recieve data of any size
    def __recv(self, client):
        if client is not None:
            client.settimeout(self.__timeout)
            try:
                buffer = b''
                while True:
                    data = client.recv(1024)
                    if len(data) < 1024:
                        # data send loop completed
                        client.settimeout(3600)
                        return buffer + data
                    buffer += data
            except Exception as e:
                client.settimeout(3600)
                return None

    # Check the code of the response
    def __check_code(self, msg):
        codes = {'231': "QUIT", '221': "QUIT", '214': 'SUCCESSFUL', '230': 'LOGGED', '500': 'ERROR',
                 '200': 'SUCCESSFUL'}
        code = msg[:3]
        if code in ['221', '231']:
            exit(-1)
        elif code == '230':
            self.__logged_in = True
        elif code[0] == '5':
            return False
        else:
            return True

    ## Add more function bellow here
    # Best way to use LIST command
    def ls(self, args, return_list=False):
        data_client = self.__pasv()
        msg = (f"LIST " + " ".join(args) + "\r\n").encode()
        self.__client.send(msg)
        ls_list = self.__recv(data_client)
        data_client.close()
        if return_list:
            return ls_list
        else:
            print_response(self.__recv(self.__client))
            print_response(ls_list)
            print_response(self.__recv(self.__client))

    # Download a file using RETR
    ## Implement the retr and wait for data in the data_client port
    def retr(self, args):
        data_client = self.__pasv()
        msg = f"RETR {args[0]}\r\n".encode()
        filename = args[0].replace('\\', '/').split('/')[-1]
        self.__client.send(msg)
        response1 = self.__recv(self.__client)
        # Start recieving
        if response1:
            # If the code is an error
            if self.__check_code(response1):
                print(response1.decode().strip())
                # File content
                file_content = self.__recv(data_client)

                print_response(self.__recv(self.__client))
                if file_content:
                    with open(filename, 'wb') as file:
                        file.write(file_content)
                        file.close()
        data_client.close()

    # Equivalent to get from FTP client in linux
    def get(self, args):
        self.retr(args)

    def mget(self, args):
        print("NOT IMPLEMENTED YET")

    # Start the connection
    def start_connection(self):
        welcome = self.__recv(self.__client).decode()
        print(welcome.strip())
        while True:
            msg = input('ftp>')
            # If not data will be send, send NOOP command (no operation)
            if not len(msg):
                msg = 'NOOP'
            # Separate authenticated session of not ayth session
            ## this let us to except an y socket block during the session
            if self.__logged_in:
                cmd, *args = getCodeOrCommand(msg)
                commandFunction = self.__getCommandString(cmd.lower())  # Method/Function of the string
                # Only execute command if is one of the allowed
                if commandFunction and cmd != 'start_connection':
                    commandFunction(args)  # Execute one implemented command
                # if no command have been found only send it raw
                else:
                    # Client for sending all the data (data port)
                    data_client = self.__pasv()
                    msg = (msg + '\r\n').encode()
                    self.__client.send(msg)
                    response1 = self.__recv(self.__client)
                    if response1:
                        print(response1.decode().strip())
                        # Only try to print the other responses if we got a successful code as response
                        if self.__check_code(response1.decode()):
                            print_response(self.__recv(data_client))
                            print_response(self.__recv(self.__client))
                    data_client.close()

            else:
                # Simple socket communication for not authenticated session
                msg = (msg + '\r\n').encode()
                self.__client.send(msg)
                response = self.__recv(self.__client).decode()
                self.__check_code(response)
                print(response.strip())


# FTP Client
class FTP:
    def __init__(self):
        self.__host = None
        self.__port = None
        self.__family = None
        self.__client = None

    # SEt the familyof the command socket
    def setfamily(self, family):
        self.__family = family

    # Set host
    def host(self, host):
        self.__host = host

    # Set port
    def port(self, port):
        self.__port = port

    # Create connection
    def __create_client(self):
        self.__client = socket(self.__family, SOCK_STREAM)
        self.__client.connect((self.__host, self.__port))

    # Start the client after setting up everything
    def start(self):
        self.__create_client()
        # Create the handlerr for the session
        handler = FTPHandler((self.__host, self.__port), self.__client)
        # Start the handler
        handler.start_connection()


def main(args=None):
    if not args:
        parser = ArgumentParser()
        parser.add_argument('HOST', help='HOST IP')
        parser.add_argument('PORT', help='PORT of the FTP server', default=21, type=int)
        parser.add_argument('-6', dest='setfamily', help='User IPV6', action='store_const', const=AF_INET6, default=AF_INET)
        args = vars(parser.parse_args())
    ftp = FTP()
    for key in args.keys():
        getattr(ftp, key.lower())(args[key])
    ftp.start()


if __name__ == '__main__':
    main()
