import requests
from time import sleep
import smtplib
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
import datetime
import json
from random import randrange
from HTMLParse import MyHTMLParser
import shutil

url_name_maps = []

sleep_seconds = 60 * 60

smtp_server = ""
smtp_from_address = ""
smtp_from_address_password = ""

smtp_recipients = []
sms_recipients = []

def send_email(to_addrs, subject, body):
    message = MIMEMultipart()
    message['From'] = smtp_from_address
    message['To'] = ", ".join(to_addrs)
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain', 'utf-8'))

    server = smtplib.SMTP(smtp_server)
    server.starttls()
    server.login(smtp_from_address, smtp_from_address_password)
    server.sendmail(smtp_from_address, to_addrs, message.as_string())
    server.quit()

def send_sms(to_addrs, body):
    server = smtplib.SMTP(smtp_server)
    server.starttls()
    server.login(smtp_from_address, smtp_from_address_password)
    server.sendmail(smtp_from_address, to_addrs, body)
    server.quit()

def generate_message(course_name, course_url):
    subject = course_name + " Webpage has Changed!"

    email_body = "This is a notification email informing you that the course website for " + course_name + " has changed since the last time we saw it."
    email_body += "\n\n Please visit " + course_url + " to see the changes."

    sms_body = "The course website for " + course_name + " has changed!"

    return {'email': email_body, 'sms': sms_body, 'subject': subject}

def read_file(course_name):
    f = open(course_name, 'r')
    data = f.read()
    f.close()
    return data

def write_file(course_name, data):
    f = open(course_name, 'w')
    f.write(data)
    f.close()

def append_file(file_name, data):
    f = open(file_name, 'a')
    f.write(data)
    f.close()

def log(course_name, course_url, changes_found):
    log_file_name = "log"
    data = "[" + str(datetime.datetime.now()) + "] "
    data += "Successfully reviewed the website for " + course_name + ": " + course_url
    if changes_found:
        data += " and changes were found! \n"
    else:
        data += "\n"
    append_file(log_file_name, data)

def load_courses():
    json_courses = open('courses.json')
    list_courses = json.load(json_courses)

    for course in list_courses:
        url = str(course["url"])
        name = str(course["name"])

        list_downloads = course["downloads"]
        downloads = []
        for download in list_downloads:
            download_dict = {}
            download_dict['url'] = download['url']
            download_dict['name'] = download['name']
            download_dict['files'] = []

            list_files = download['files']
            for file_desc in list_files:
                file_dict = {}
                file_dict['name'] = file_desc['name']
                file_dict['directory'] = file_desc['directory']
                file_dict['format'] = file_desc['format']
                file_dict['extension'] = file_desc['extension']
                download_dict['files'].append(file_dict)

            downloads.append(download)

        url_name_maps.append({
            'url': url,
            'name': name,
            'downloads': downloads
        })

def load_emails():
    json_emails = open('email.json')
    list_emails = json.load(json_emails)

    for email in list_emails:
        smtp_recipients.append(str(email))

def load_sms():
    json_sms = open('sms.json')
    list_sms = json.load(json_sms)

    for sms in list_sms:
        sms_recipients.append(str(sms))

def load_smtp_configuration():
    json_config = open('smtp_configuration.json')
    config = json.load(json_config)

    smtp_server = str(config["smtpServer"])
    smtp_from_address = str(config["smtpFromAddress"])
    smtp_from_address_password = str(config["smtpFromAddressPassword"]) 

    return smtp_server, smtp_from_address, smtp_from_address_password

def compare_files(old_file, new_file, file_name_pattern, desired_file_extension):
    old_parser = MyHTMLParser()
    old_parser.feed(old_file)

    new_parser = MyHTMLParser()
    new_parser.feed(new_file)

    old_anchors = old_parser.anchors
    new_anchors = new_parser.anchors

    old_parser.close()
    new_parser.close()

    new_files_to_download = []

    for anchor in new_anchors:
        if anchor not in old_anchors:
            # this is a new anchor tag added to the file, likely linking to a new file to download
            if anchor[-4:] == desired_file_extension:
                # If this anchor has the right file extension
                if str.startswith(anchor, file_name_pattern):
                    # If the file starts with the right pattern string
                    # go ahead and download this file
                    new_files_to_download.append(anchor)


    return new_files_to_download

def download_file(file_url, destination_directory, destination_file_name):

    full_path = destination_directory

    if full_path[:-1] != "/":
        full_path += "/"

    full_path += destination_file_name

    r = requests.get(file_url, stream=True)

    with open(full_path, 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)

    del r

load_courses()
load_emails()
load_sms()
smtp_server, smtp_from_address, smtp_from_address_password = load_smtp_configuration()

while(True):
    for entry in url_name_maps:
        for download in entry['downloads']:
            try:
                r = requests.get(download['url'])
                try:
                    old_file = read_file(entry['name'] + "/" + download['name'])
                except IOError:
                    # File doesn't exist yet
                    old_file = ""

                changes_found = False

                if r.text != old_file and r.text != "":

                    for file_type in download['files']:

                        files_to_download = compare_files(old_file, r.text, file_type['format'], file_type['extension'])

                        if len(files_to_download) > 0:
                            changes_found = True
                            for new_file in files_to_download:

                                url = download['url'] + "/" + new_file
                                
                                download_file(url, file_type['directory'], new_file)

                    message = generate_message(entry['name'], download['url'])

                    send_email(smtp_recipients, str(message['subject']), str(message['email']))
                    send_sms(sms_recipients, message['sms'])

                    write_file(entry['name'] + "/" + download['name'], r.text)
                    
                log(entry['name'], download['url'], changes_found)
                sleep(randrange(30,60))

            except requests.exceptions.ConnectionError:
                # No Internet Connection
                pass
        sleep(sleep_seconds)

