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

    def delete_torrent_by_id(self, download_id):
        api_path = '/api/transfer/delete?type=torrent&id=' + download_id
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

    def get_folder_key_for_torrent_by_id(self, download_id, key):
        transfer_list = self.list_transfers()
        if transfer_list and transfer_list['status'] == 'success':
            for download in transfer_list['transfers']:
                if download.get('id') == download_id:
                    return download[key]

    def get_folder_id_for_torrent_by_id(self, download_id):
        return self.get_folder_key_for_torrent_by_id(download_id, 'folder_id')

    def get_folder_name_for_torrent_by_id(self, download_id):
        return self.get_folder_key_for_torrent_by_id(download_id, 'name')

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
        folder_id = self.get_folder_id_for_torrent_by_id(download_id)
        return self.list_urls_for_torrent_by_folder_id(folder_id, '.')

    def list_urls_for_torrent_by_folder_id(self, folder_id, parent_name):
        torrent = self.browse_torrent_by_folder_id(folder_id)
        if torrent['status'] == 'success':
            return self._urls_for_child(torrent['content'], parent_name)
        else:
            return []

    def _urls_for_child(self, children, parent_name):
        urls = []
        for file_or_folder in children:
            if file_or_folder['type'] == 'file':
                url = file_or_folder.get('link')
                if url:
                    urls.append({'path': parent_name, 'url': url})
            elif file_or_folder['type'] == 'folder':
                urls += self.list_urls_for_torrent_by_folder_id(file_or_folder['id'], file_or_folder['name'])
            else:
                raise ValueError("%s is not a valid object type" % file_or_folder['type'])
        return urls

    def browse_torrent_by_folder_id(self, folder_id):
        api_path = '/api/folder/list?id=%s' % folder_id
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
        try:
            request = requests.post(host + path, params=params, files=files)
            request.raise_for_status()
        except requests.exceptions.RequestException as e:
            # TODO: handle specific errors like: requests.exceptions.ConnectionError 104
            print('Error requests:', e, )
            return
        if request.status_code == requests.codes.ok:
            return json.loads(request.text)
        else:
            # TODO: handle 502 bad gateway from cloudflare
            print('Error no http ok:', request, )
            return
