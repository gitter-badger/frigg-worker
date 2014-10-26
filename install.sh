# Install script, meant to be run with:
#   curl https://raw.githubusercontent.com/frigg/frigg-worker/master/install.sh | sh
# Does the following:
#   * Add user frigg-worker
#   * Create virtualenvironment in /home/frigg-worker/frigg-worker/
#   * Install frigg-worker in that virtualenvironment
#   * Install and setup supervisor

USERNAME=frigg-worker
VENV=/home/$USERNAME/frigg-worker/

echo "Installing pip"
which pip || apt-get install -q python-pip

echo "Installing virtualenv"
which virtualenv || apt-get install -q python-virtualenv

echo "Installing supervisor"
which supervisord || apt-get install -q supervisor

echo "Adding user ${USERNAME}"
adduser --disabled-password --gecos "" $USERNAME

echo "Installing frigg-worker"
su -c $USERNAME "virtualenv ${VENV} && ${VENV}/bin/pip install -e git+https://github.com/frigg/frigg-worker.git#egg=frigg-worker"

# FIXME, replace with line below when it's ready:
# $VENV/bin/frigg-worker supervisor-config > /etc/supervisord/conf.d/frigg-worker.conf
echo "[program:frigg-worker]
directory=/home/${USERNAME}/
command=${VENV}bin/frigg-worker start
autostart=true
autorestart=true
redirect_stderr=true
user=frigg" > /etc/supervisord/conf.d/frigg-worker.conf

supervisorctl reload
supervisorctl start
