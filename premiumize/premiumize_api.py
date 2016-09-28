import requests
import json

class PremiumizeApi:
    def __init__(self, customer_id, pin):
        self.customer_id = customer_id
        self.pin = pin

    def print_usage(self):
        print('hello')

    def list_transfers(self):
        api_path = '/api/transfer/list'
        response = self.post_to_api(api_path)
        return response

    def root_folder_list(self):
        api_path = '/api/folder/list'
        response = self.post_to_api(api_path)
        return response

    def get_transfer_status_for_hash(self, transfer_hash):
        transfers = self.list_transfers()
        if transfers['status'] == 'success':
            for transfer in transfers['transfers']:
                if transfer['hash'] == transfer_hash:
                    return transfer['status']
            return 'not found'

    def delete_finished_torrent_by_id(self, download_id):
        download_hash = self.get_hash_for_id(download_id)
        self.delete_finished_torrent_by_hash(download_hash)

    def delete_finished_torrent_by_hash(self, download_hash):
        if self.get_transfer_status_for_hash(download_hash) == 'finished':
            return self.delete_torrent_by_hash(download_hash)
        else:
            error = {
                'status': 'error',
                'message': 'Download is not yet finished'
            }
            return error

    def delete_torrent_by_id(self, download_id):
        api_path = '/api/transfer/delete?type=torrent&id=' + download_id
        response = self.post_to_api(api_path)
        return response

    def delete_torrent_by_hash(self, download_hash):
        api_path = '/api/transfer/delete?type=torrent&id=' + download_hash
        response = self.post_to_api(api_path)
        return response

    def get_hash_for_id(self, download_id):
        folder_list = self.root_folder_list()
        if folder_list['status'] == 'success':
            for download in folder_list['content']:
                if download['id'] == download_id:
                    return download['hash']

    def list_folders(self):
        api_path = '/api/folder/list'
        response = self.post_to_api(api_path)
        return response

    def get_folder_name_for_torrent_by_hash(self, download_hash):
        folder_list = self.list_folders()
        if folder_list and folder_list['status'] == 'success':
            for download in folder_list['content']:
                if download.get('hash') == download_hash:
                    return download['name']

    def list_items(self, where='transfers', what='hash'):
        uploaded_ids = set()

        if where == 'folders':
            response = self.list_folders()
            data = 'content'
        elif where == 'transfers':
            response = self.list_transfers()
            data = 'transfers'
        else:
            return uploaded_ids

        if response['status'] == 'success':
            folders = response[data]
            for i in (folder.get(what) for folder in folders):
                if i:
                    uploaded_ids.add(i)

        return uploaded_ids

    def list_urls_for_torrent_by_id(self, download_id):
        download_hash = self.get_hash_for_id(download_id)
        self.list_urls_for_torrent_by_hash(download_hash)

    def list_urls_for_torrent_by_hash(self, download_hash):
        torrent = self.browse_torrent_by_hash(download_hash)
        urls = set()
        if torrent['status'] == 'success':
            urls |= self._urls_for_child(torrent['content'])
        return urls

    def _urls_for_child(self, children):
        urls = set()
        for key in children.keys():
            child = children[key]
            url = child.get('url')
            if url:
                urls.add(url)
            new_children = child.get('children')
            if new_children:
                    urls |= self._urls_for_child(new_children)
        return urls

    def browse_torrent_by_hash(self, download_hash):
        api_path = '/api/torrent/browse?hash=' + download_hash
        response = self.post_to_api(api_path)
        return response

    def upload_torrent_file(self, file_path):
        api_path = '/api/transfer/create?type=torrent&src=SRC'
        files = {
            'src': open(file_path, 'rb')
        }
        response = self.post_to_api(api_path, files)
        return response

    def send_magnet_link(self, magnet_link):
        api_path = '/api/transfer/create?type=torrent&src={}'.format(magnet_link)
        response = self.post_to_api(api_path)
        return response

    def post_to_api(self, path, files={}):
        host = 'https://www.premiumize.me'
        params = {
            'customer_id': self.customer_id,
            'pin': self.pin
        }
        request = requests.post(host + path, params=params, files=files)
        if request.status_code == requests.codes.ok:
            return json.loads(request.text)
        else:
            # TODO: handle 502 bad gateway from cloudflare
            print('Error:', request, )
            return
