from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="DeepBug/RideSafe-400",
    repo_type="dataset",
    local_dir="ridesafe_raw"
)

print("Download complete")