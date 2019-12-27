from __future__ import print_function
import smtplib
import configparser
import csv
import sys
import logging
import pickle
import os.path
import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.text import MIMEText
from email.headerregistry import Address
from datetime import timedelta, date

SCOPES = ['https://mail.google.com/']
configfile='config.ini'
logging.basicConfig(filename="spammer.log",
                    filemode='w',
                    format='%(name)s - %(levelname)s - %(message)s'
                    )

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def read_config():
    config = configparser.ConfigParser()
    try:
        config.read(configfile)   
    except:
        errormsg="File %s doesn't exist" % configfile
        logging.error(errormsg)
        print_error(errormsg)
    return config 

def print_error(message):
    print(bcolors.WARNING+'[E]'+bcolors.ENDC+' %s' % message)
    sys.exit(1)

def print_info(message):
    print(bcolors.OKBLUE+'[i]'+bcolors.ENDC+' %s' % message)

def print_success(message):
    print(bcolors.OKGREEN+'[+]'+bcolors.ENDC+' %s' % message)

def create_email(config, to_address, body):
    from_user,from_domain=parse_address(config['HEADERS']['SENDER_ADDRESS'])
    reply_user,reply_domain=parse_address(config['HEADERS']['REPLYTO_ADDRESS'])
    message = MIMEText(body)
    message['from'] = str(Address(config['HEADERS']['SENDER_NAME'],from_user,from_domain))
    message['reply-to'] = str(Address(config['HEADERS']['REPLYTO_NAME'],reply_user,reply_domain))
    message['to'] = str(to_address)
    message['bcc'] = str(Address("HelSec Ry","contact","helsec.fi"))
    message['subject'] = str(config['HEADERS']['SUBJECT'])
    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    msg = {'raw': raw}
    return msg

def parse_address(address):
    username=address.split("@")[0]
    domain=address.split("@")[1]
    return username,domain

def get_items(row, config):
    order_made=row[0]
    email_address=row[1]
    item1=is_ordered(config['ITEMS']['item1']+':'+row[2])
    item2=is_ordered(config['ITEMS']['item2']+':'+row[4])
    item3=is_ordered(config['ITEMS']['item3']+':'+row[5])
    item4=is_ordered(config['ITEMS']['item4']+':'+row[6])
    item5=is_ordered(config['ITEMS']['item5']+':'+row[7])
    firstname=row[8]
    member=is_member(row[10])
    delivery_method=row[11]
    refnum=row[14]
    return order_made, email_address, item1, item2, item3, item4, item5, firstname, member, delivery_method, refnum

def is_ordered(item):
    if "No" in item:
        return False
    if item.split(":")[1]=="":
        return False
    else:
        if "beanie" in item:
            item=item.split(":")[0]
            return item
        if "bag" in item:
            item=item.split(":")[0]
            return item
        else:
            return item

def is_member(string):
    if string != "":
        return True
    else:
        return False

def build_body(config, firstname, order_made, pyshoodie, beshirt, pystshirt, kassit, pipa, member, delivery_method,reference_nro):
    body=[]
    body.append("Hey %s,\n\n" % firstname)
    body.append(config['BODY']['START']+'\n\n')
    recap=[]
    recap.append(config['BODY']['ITEMS']+'\n')
    items=[pyshoodie, beshirt, pystshirt, kassit, pipa]
    total=0
    for item in items:
        if item==False:
            continue
        else:
            if member==True:
                if "hoodie" in item:
                    price=config['ITEMS']['item1_mprice']
                if "believe" in item:
                    price=config['ITEMS']['item2_mprice']
                if "vetää\" T-shirt" in item:
                    price=config['ITEMS']['item3_mprice']
                if "shopping" in item:
                    #print("IHAZTHEBAG")
                    price=config['ITEMS']['item4_mprice']
                if "beanie" in item:
                    price=config['ITEMS']['item5_mprice']
            if member==False:
                if "hoodie" in item:
                    price=config['ITEMS']['item1_price']
                if "believe" in item:
                    price=config['ITEMS']['item2_price']
                if "vetää\" T-shirt" in item:
                    price=config['ITEMS']['item3_price']
                if "shopping" in item:
                    #print("IHAZTHEBAG")
                    price=config['ITEMS']['item4_price']
                if "beanie" in item:
                    price=config['ITEMS']['item5_price']
            #if ":" in item:
            #    recap.append(item.split(":")[0]+", "+price+"€\n")
            #else:
            recap.append("✓ "+item+", "+price+"€\n")
            total=total+int(price)
    if "Posti Oyj" in delivery_method:
        total=total+7.90
    recap.append("Total amount %s€ (%s)" % (total, delivery_method))
    body.append("".join(recap)+"\n\n")
    body.append("Payment details\n")
    body.append("Receiver: ")
    body.append(config['BODY']['ACCOUNT_HOLDER']+'\n')
    body.append("Account number: ")
    body.append(config['BODY']['ACCOUNT_NUMBER']+'\n')
    body.append("SWIFT/BIC: ")
    body.append(config['BODY']['ACCOUNT_SWIFT']+'\n')
    body.append("Reference: ")
    body.append(str(reference_nro)+'\n')
    body.append("Amount: ")
    body.append(str(total)+' €\n')
    body.append("Due date: ")
    duedate=date.today() + timedelta(days=7)
    body.append(str(duedate)+'\n\n')
    body.append(config['BODY']['END']+'\n\n')
    body.append('Your order was made on %s.\n\n' % order_made)
    body.append("With best regards,\n")
    body.append(config['BODY']['SIGNATURE']+"\n\n")
    return "".join(body)    

def open_connection(config):
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                   "credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    return service

def send_email(service, email, config):
    try:
        userid=config['HEADERS']['SENDER_ADDRESS']
        #userid="me"
        message = (service.users().messages().send(userId=userid, body=email).execute())
        logging.warning(message)
        return message
    except Exception as error:
        print_error("Message could not be send:\n %s" % error)
        logging.error("Message could not be send:\n %s" % error)
        sys.exit(1)

def main():
    config=read_config()
    service=open_connection(config)
    with open('swagorder.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            email=""
            if row[0]=="Timestamp":
                print_info("Started to handle the given CSV-file")
                continue
            if row[0]=="":
                print_success("All rows done!")
                break
            else:
                order_made, email_address, pyshoodie, beshirt, pystshirt, kassit, pipa, firstname, member, delivery_method, refnum = get_items(row, config)
                print_info("Handling %s's order !" % firstname)
                email_body=build_body(config, firstname, order_made, pyshoodie, beshirt, pystshirt, kassit, pipa, member, delivery_method, refnum)
                to_username,to_domain=parse_address(email_address)
                recipient=Address(firstname,to_username,to_domain)
                email=create_email(config, recipient, email_body)
                # SAFE MODE :D UNCOMMENT THE LINE BELOW TO SEND MESSAGES
                #sent_message=send_email(service, email, config)
                logging.warning("This email was sent to %s:\n%s" % (recipient, email))
                logging.warning("Previous body in cleartext:\n %s" % email_body)
                print_success("Email sent to %s" % recipient)

if __name__ == "__main__":
    main()

#try:
#    server = smtplib.SMTP('smtp.gmail.com', 587)
#    server.ehlo()
#except:
#    print 'Something went wrong...'
