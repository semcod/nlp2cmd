"""
DevOps domain templates for NLP2CMD.

Contains CI/CD, deployment, monitoring, Ansible, Terraform, systemctl templates.
"""

DEVOPS_TEMPLATES = {
    # Systemctl / services
    'service_start': "sudo systemctl start {service}",
    'service_stop': "sudo systemctl stop {service}",
    'service_restart': "sudo systemctl restart {service}",
    'service_reload': "sudo systemctl reload {service}",
    'service_status': "sudo systemctl status {service}",
    'service_enable': "sudo systemctl enable {service}",
    'service_disable': "sudo systemctl disable {service}",
    'service_logs': "journalctl -u {service} -n {lines} --no-pager",
    'service_list': "systemctl list-units --type=service --state=running",
    'service_failed': "systemctl --failed",
    # Ansible
    'ansible_ping': "ansible {hosts} -m ping",
    'ansible_command': "ansible {hosts} -m command -a '{command}'",
    'ansible_playbook': "ansible-playbook {playbook}",
    'ansible_playbook_check': "ansible-playbook --check {playbook}",
    'ansible_playbook_limit': "ansible-playbook {playbook} --limit {hosts}",
    'ansible_playbook_tags': "ansible-playbook {playbook} --tags {tags}",
    'ansible_inventory': "ansible-inventory --list",
    'ansible_galaxy_install': "ansible-galaxy install {role}",
    'ansible_vault_encrypt': "ansible-vault encrypt {file}",
    'ansible_vault_decrypt': "ansible-vault decrypt {file}",
    'ansible_facts': "ansible {hosts} -m setup",
    # Terraform
    'terraform_init': "terraform init",
    'terraform_plan': "terraform plan",
    'terraform_apply': "terraform apply",
    'terraform_apply_auto': "terraform apply -auto-approve",
    'terraform_destroy': "terraform destroy",
    'terraform_destroy_auto': "terraform destroy -auto-approve",
    'terraform_output': "terraform output",
    'terraform_state_list': "terraform state list",
    'terraform_state_show': "terraform state show {resource}",
    'terraform_import': "terraform import {resource} {id}",
    'terraform_validate': "terraform validate",
    'terraform_fmt': "terraform fmt",
    'terraform_workspace_list': "terraform workspace list",
    'terraform_workspace_new': "terraform workspace new {name}",
    'terraform_workspace_select': "terraform workspace select {name}",
    # CI/CD
    'github_actions_run': "gh workflow run {workflow}",
    'github_actions_list': "gh run list",
    'github_actions_view': "gh run view {run_id}",
    'github_actions_logs': "gh run view {run_id} --log",
    'gitlab_ci_trigger': "curl -X POST -F token={token} -F ref={branch} {gitlab_url}/api/v4/projects/{project_id}/trigger/pipeline",
    # Monitoring
    'prometheus_query': "curl -s '{prometheus_url}/api/v1/query?query={query}'",
    'grafana_dashboard': "curl -s -H 'Authorization: Bearer {token}' '{grafana_url}/api/dashboards/uid/{uid}'",
    'check_port': "ss -tuln | grep {port}",
    'check_health': "curl -sf {url}/health || echo 'unhealthy'",
    'check_endpoint': "curl -w '%{{http_code}}' -sf -o /dev/null {url}",
    # Nginx
    'nginx_test': "sudo nginx -t",
    'nginx_reload': "sudo systemctl reload nginx",
    'nginx_logs_access': "tail -f /var/log/nginx/access.log",
    'nginx_logs_error': "tail -f /var/log/nginx/error.log",
    # Cron
    'cron_list': "crontab -l",
    'cron_edit': "crontab -e",
    'cron_add': "echo '{schedule} {command}' | crontab -",
    # SSL/TLS
    'ssl_check': "openssl s_client -connect {host}:443 -servername {host} </dev/null 2>/dev/null | openssl x509 -noout -dates",
    'ssl_certbot': "sudo certbot --nginx -d {domain}",
    'ssl_certbot_renew': "sudo certbot renew",
    # Logs
    'journalctl_follow': "journalctl -f",
    'journalctl_unit': "journalctl -u {service} --since '{since}'",
    'journalctl_errors': "journalctl -p err --since '{since}'",
    'dmesg_tail': "dmesg | tail -n {lines}",
}
