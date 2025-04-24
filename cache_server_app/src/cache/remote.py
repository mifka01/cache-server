import json
import urllib.request
import urllib.error

class RemoteCacheHelper:
    """Utility class for remote cache operations."""

    def __init__(self, cache):
        self.cache = cache
        self.cached_paths = {}

    def get_remote_cache_url(self, key_hash):
        """
        Lookup a remote cache URL from DHT using the provided hash.
        Returns the remote cache URL or None if not found.
        """
        remote_cache_id = self.cache.dht.get(key_hash)
        if not remote_cache_id or not remote_cache_id[0]:
            return None

        remote_cache = self.cache.dht.get(remote_cache_id[0])
        if not remote_cache or not remote_cache[0]:
            return None

        try:
            remote_cache_url = json.loads(remote_cache[0]).get("url")
            return remote_cache_url if remote_cache_url else None
        except json.JSONDecodeError:
            print(f"ERROR: Invalid JSON in remote cache data for {key_hash}")
            return None

    def fetch_and_process_remote_narinfo(self, store_hash, remote_cache_url):
        """Fetch narinfo from remote cache and process it."""
        try:
            remote_url = f"{remote_cache_url}/{store_hash}.narinfo"
            with urllib.request.urlopen(remote_url) as resp:
                if resp.status != 200:
                    return None, resp.status

                narinfo_data = resp.read()
                narinfo_dict = self.cache.sign(narinfo_data)

                file_url = narinfo_dict.get("URL")
                if file_url:
                    self.cached_paths[file_url] = remote_cache_url

                ordered_keys = [
                    "StorePath", "URL", "Compression", "FileHash", "FileSize",
                    "NarHash", "NarSize", "Deriver", "System", "References", "Sig"
                ]

                response = ""
                for key in ordered_keys:
                    value = narinfo_dict.get(key, "")
                    if key == "References" and value:
                        value = " ".join(value)
                    response += f"{key}: {value}\n"

                return response.encode(), 200
        except urllib.error.URLError as e:
            print(f"ERROR: Failed to fetch remote narinfo: {e}")
            return None, 502
        except Exception as e:
            print(f"ERROR: Unexpected error fetching narinfo: {e}")
            return None, 500

    def fetch_remote_nar_file(self, file_hash, compression, remote_cache_url):
        """Fetch nar file from remote cache."""
        nar_path = f"nar/{file_hash}.nar.{compression}"
        try:
            remote_url = f"{remote_cache_url}/{nar_path}"
            with urllib.request.urlopen(remote_url) as resp:
                if resp.status != 200:
                    return None, resp.status

                nar_data = resp.read()

                # Consider caching the file locally to avoid future redirects
                # try:
                #     self.cache.storage.save(f"{file_hash}.nar.{compression}", nar_data)
                # except Exception as cache_err:
                #     print(f"Failed to cache remote nar file locally: {cache_err}")

                # Remove the mapping after successful fetch
                if nar_path in self.cached_paths:
                    self.cached_paths.pop(nar_path)

                return nar_data, 200
        except urllib.error.URLError as e:
            print(f"ERROR: Failed to fetch remote nar file: {e}")
            return None, 502
        except Exception as e:
            print(f"ERROR: Unexpected error fetching nar file: {e}")
            return None, 500
