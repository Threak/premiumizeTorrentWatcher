#!/usr/bin/env python

from premiumize import premiumize_api as api
from os import walk, remove, makedirs, rename
from os.path import join, exists
from json import dumps
from subprocess import call
import configparser
import threading
import time

CONFIG_PATH = 'config.ini'
config = configparser.ConfigParser()
config.read(CONFIG_PATH)

UPLOADED_IDS = set()

premiumize_api = api.PremiumizeApi(config['PREMIUMIZE']['CustomerId'], config['PREMIUMIZE']['Pin'])

def print_json(json):
    print(dumps(json, sort_keys=True, indent=4))

def save_new_id(old_ids):
    all_ids = premiumize_api.list_folder('hash')
    new_ids = all_ids - old_ids
    if new_ids:
        new_id = new_ids.pop()
        config.read(CONFIG_PATH)
        config['DOWNLOADS']['Hashes'] = config['DOWNLOADS']['Hashes'] + ',' + new_id
        save_config_file()

def upload_torrent_from_folder():
    torrent_folder = config['TORRENT']['TorrentFilesLocation']
    if not exists(torrent_folder):
        makedirs(torrent_folder)

    while True:
        for (dirpath, dirnames, filenames) in walk(torrent_folder):
            for filename in filenames:
                if filename.endswith('.torrent'):
                    filepath = join(dirpath, filename)
                    print('Now uploading: ', filename)
                    old_folder_ids = premiumize_api.list_folder('hash')
                    upload = premiumize_api.upload_torrent_file(filepath)
                    if upload['status'] == 'success':
                        print('Successfully uploaded: ' + filename)
                        save_new_id(old_folder_ids)
                        if config['TORRENT'].getboolean('DeleteTorrentOnSuccess', fallback=True):
                            remove(filepath)
                    else:
                        print('Error:', upload['message'], 'in file', filename)
                        if upload['message'] == 'This torrent is already in the download list.':
                            save_new_id(old_folder_ids)
                            if config['TORRENT'].getboolean('DeleteTorrentOnDuplicate', fallback=True):
                                print('Deleting already existing torrent: ' + filename)
                                remove(filepath)
                print()
        time.sleep(10)

def download_finished_torrents():
    download_folder = config['TORRENT']['DownloadDirectory']
    if not exists(download_folder):
        makedirs(download_folder)

    finished_folder = config['TORRENT']['FinishedDownloadDirectory']
    if not exists(finished_folder):
        makedirs(finished_folder)

    while True:
        config.read(CONFIG_PATH)
        download_hash_list = config['DOWNLOADS']['Hashes'].split(',')
        finished_hash_list = set()
        for download_hash in download_hash_list:
            folder_name = premiumize_api.get_folder_name_for_torrent_by_hash(download_hash)
            if not folder_name:
                continue
            download_target = join(download_folder, folder_name)
            download_finished = join(finished_folder, folder_name)
            if not exists(download_target):
                makedirs(download_target)
            if not exists(download_finished):
                makedirs(download_finished)
            downloads = premiumize_api.list_urls_for_torrent_by_hash(download_hash)
            for download in downloads:
                call(['aria2c', '--file-allocation=falloc', '-c', '-d', download_target, download])
            rename(download_target, download_finished)
            if config['TORRENT'].getboolean('DeleteFinishedTorrent', fallback=True):
                print('Deleting torrent:', folder_name)
                premiumize_api.delete_torrent_by_hash(download_hash)
            finished_hash_list.add(download_hash)
            config.read(CONFIG_PATH)
            new_download_hash_list = config['DOWNLOADS']['Hashes'].split(',')
            remaining_hash_list = set(new_download_hash_list) - finished_hash_list
            config['DOWNLOADS']['Hashes'] = ','.join(remaining_hash_list)
            save_config_file()
        time.sleep(30)

def save_config_file():
    with open(CONFIG_PATH, 'w') as configfile:
        config.write(configfile)

upload = threading.Thread(target=upload_torrent_from_folder)
upload.start()

download = threading.Thread(target=download_finished_torrents)
download.start()
