"""
Remote execution domain templates for NLP2CMD.

Contains SSH, SCP, rsync, tmux, remote management templates.
"""

REMOTE_TEMPLATES = {
    # SSH
    'ssh_connect': "ssh {user}@{host}",
    'ssh_command': "ssh {user}@{host} '{command}'",
    'ssh_port': "ssh -p {port} {user}@{host}",
    'ssh_key': "ssh -i {key} {user}@{host}",
    'ssh_tunnel': "ssh -L {local_port}:{remote_host}:{remote_port} {user}@{host}",
    'ssh_reverse_tunnel': "ssh -R {remote_port}:{local_host}:{local_port} {user}@{host}",
    'ssh_socks_proxy': "ssh -D {port} {user}@{host}",
    'ssh_background': "ssh -fN -L {local_port}:{remote_host}:{remote_port} {user}@{host}",
    'ssh_keygen': "ssh-keygen -t {type} -b {bits} -f {file} -C '{comment}'",
    'ssh_keygen_ed25519': "ssh-keygen -t ed25519 -C '{comment}'",
    'ssh_copy_id': "ssh-copy-id {user}@{host}",
    'ssh_config_test': "ssh -T {user}@{host}",
    'ssh_jump': "ssh -J {jump_host} {user}@{host}",
    'ssh_agent': "eval $(ssh-agent -s) && ssh-add {key}",
    # SCP
    'scp_upload': "scp {local_path} {user}@{host}:{remote_path}",
    'scp_download': "scp {user}@{host}:{remote_path} {local_path}",
    'scp_recursive': "scp -r {local_path} {user}@{host}:{remote_path}",
    'scp_port': "scp -P {port} {local_path} {user}@{host}:{remote_path}",
    'scp_key': "scp -i {key} {local_path} {user}@{host}:{remote_path}",
    # rsync
    'rsync_sync': "rsync -avz {source} {user}@{host}:{destination}",
    'rsync_download': "rsync -avz {user}@{host}:{source} {destination}",
    'rsync_dry_run': "rsync -avzn {source} {user}@{host}:{destination}",
    'rsync_delete': "rsync -avz --delete {source} {user}@{host}:{destination}",
    'rsync_exclude': "rsync -avz --exclude '{pattern}' {source} {user}@{host}:{destination}",
    'rsync_progress': "rsync -avz --progress {source} {user}@{host}:{destination}",
    'rsync_ssh_port': "rsync -avz -e 'ssh -p {port}' {source} {user}@{host}:{destination}",
    'rsync_bandwidth': "rsync -avz --bwlimit={limit} {source} {user}@{host}:{destination}",
    # tmux
    'tmux_new': "tmux new-session -s {name}",
    'tmux_attach': "tmux attach-session -t {name}",
    'tmux_detach': "tmux detach-client",
    'tmux_list': "tmux list-sessions",
    'tmux_kill': "tmux kill-session -t {name}",
    'tmux_split_h': "tmux split-window -h",
    'tmux_split_v': "tmux split-window -v",
    'tmux_send': "tmux send-keys -t {session} '{command}' Enter",
    # screen
    'screen_new': "screen -S {name}",
    'screen_attach': "screen -r {name}",
    'screen_list': "screen -ls",
    'screen_detach': "screen -d {name}",
    # Remote execution
    'parallel_ssh': "parallel-ssh -h {hosts_file} -i '{command}'",
    'pdsh': "pdsh -w {hosts} '{command}'",
    'fabric': "fab -H {host} -- '{command}'",
    # Wake-on-LAN
    'wol': "wakeonlan {mac_address}",
    'etherwake': "sudo etherwake {mac_address}",
    # VPN
    'wireguard_up': "sudo wg-quick up {interface}",
    'wireguard_down': "sudo wg-quick down {interface}",
    'wireguard_status': "sudo wg show",
    'openvpn_connect': "sudo openvpn --config {config_file}",
}
