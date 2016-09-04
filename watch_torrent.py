#!/usr/bin/env python

from premiumize import premiumize_api as api
from os import walk, remove, makedirs, rename
from os.path import join, exists, expanduser, dirname
from shutil import copyfile
from json import dumps
from subprocess import call
import configparser
import threading
import time
import sys

CONFIG_PATH = expanduser('~/.ptw/ptw_config.ini')

def print_json(json):
    print(dumps(json, sort_keys=True, indent=4))

def save_new_id(new_id):
    config.read(CONFIG_PATH)
    config['DOWNLOADS']['Hashes'] = config['DOWNLOADS']['Hashes'] + ',' + new_id
    save_config_file()

def upload_torrent_from_folder():
    torrent_folder = config['TORRENT']['TorrentFilesLocation']

    if not exists(torrent_folder):
        makedirs(torrent_folder)

    print('Watching for new *.torrent and *.magnet files in {}'.format(torrent_folder))

    while True:
        for (dirpath, dirnames, filenames) in walk(torrent_folder):
            for filename in filenames:
                if filename.endswith('.torrent') or filename.endswith('.magnet'):
                    filepath = join(dirpath, filename)
                    print('Now uploading: ', filename)
                    if filename.endswith('.torrent'):
                        upload = premiumize_api.upload_torrent_file(filepath)
                    else:
                        with open(filepath, 'r') as magnet_file:
                            upload = premiumize_api.send_magnet_link(magnet_file.read())
                    if 'status' in upload and upload['status'] == 'success':
                        print('Successfully uploaded: ' + filename)
                        save_new_id(upload['id'])
                        if config['TORRENT'].getboolean('DeleteTorrentOnSuccess', fallback=True):
                            remove(filepath)
                        else:
                            rename(filepath, '{}.done'.format(filepath))
                    else:
                        error_filepath = '{}.error'.format(filepath)
                        rename(filepath, error_filepath)
                        if 'message' in upload:
                            print('Error:', upload['message'], 'in file', filename)
                            if upload['message'] == 'This torrent is already in the download list.':
                                # save_new_id(upload['id']) not yet implemented by API
                                if config['TORRENT'].getboolean('DeleteTorrentOnDuplicate', fallback=True):
                                    print('Deleting already existing torrent: ' + filename)
                                    remove(error_filepath)
                        else:
                            print('Error:', 'unknown (no message)', 'in file', filename)

                    print()
        time.sleep(10)

def download_finished_torrents():
    download_folder = config['TORRENT']['DownloadDirectory']
    if not exists(download_folder):
        makedirs(download_folder)

    finished_folder = config['TORRENT']['FinishedDownloadDirectory']
    if not exists(finished_folder):
        makedirs(finished_folder)

    print('Downloading finished torrent to {}, moving to {} on success.'.format(download_folder, finished_folder))

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
            downloads = premiumize_api.list_urls_for_torrent_by_hash(download_hash)
            for download in downloads:
                call(['aria2c', '--file-allocation=falloc', '--show-console-readout=false', '-c', '-d', download_target, download])
            if not exists(download_finished):
                makedirs(download_finished)
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

config_folder = dirname(CONFIG_PATH)
if not exists(config_folder):
    makedirs(config_folder)

if not exists(CONFIG_PATH):
    config_skel_path = join(dirname(__file__), 'config.ini.skel')
    copyfile(config_skel_path, CONFIG_PATH)
    print("A new config file in {} has been created.".format(CONFIG_PATH))
    print("Please add your login info and paths")
    sys.exit(-1)

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

premiumize_api = api.PremiumizeApi(config['PREMIUMIZE']['CustomerId'], config['PREMIUMIZE']['Pin'])

upload = threading.Thread(target=upload_torrent_from_folder)
upload.start()

download = threading.Thread(target=download_finished_torrents)
download.start()
