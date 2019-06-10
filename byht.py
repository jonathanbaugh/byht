import os
import shutil
import subprocess

import click
import git
import requests
import yaml

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper


BYHT_DIR = os.environ.get("BYHT_DIR", os.path.join(os.environ['HOME'], ".byht"))
BYHT_DIR_BIN = os.environ.get("BYHT_DIR_BIN", os.path.join(BYHT_DIR, "bin"))
BYHT_DIR_CACHE = os.environ.get("BYHT_DIR_CACHE", os.path.join(BYHT_DIR, "cache"))
BYHT_DIR_CONFIG = os.environ.get("BYHT_DIR_CONFIG", os.path.join(BYHT_DIR, "config.yaml"))
BYHT_DIR_COMMANDS = os.environ.get("BYHT_DIR_COMMANDS", os.path.join(BYHT_DIR, "commands"))
BYHT_REPO = os.environ.get("BYHT_REPO", "http://by.ht/index.yaml")
BYHT_LOCAL_INDEX = os.environ.get("BYHT_LOCAL_INDEX", os.path.join(BYHT_DIR_CACHE, 'index.yaml'))


class byht():
    @staticmethod
    def get_index(repo, no_cache=None, save_cache=True):
        if no_cache is None:
            no_cache = False

        if not no_cache and os.path.exists(BYHT_LOCAL_INDEX):
            with open(BYHT_LOCAL_INDEX, 'r') as fh:
                return yaml.load(fh, Loader=Loader)

        if no_cache and not save_cache:
            return yaml.load(requests.get(BYHT_REPO).content, Loader=Loader)

        with open(BYHT_LOCAL_INDEX, 'w') as fh:
            response = requests.get(BYHT_REPO)
            fh.write(response.content.decode('utf-8'))
            return yaml.load(response.content, Loader=Loader)
    
    @staticmethod
    def get_package(name):
        config = byht.get_index(BYHT_REPO)
        for package in config.get("packages", []):
            if package.get("name") == name:
                return package
        raise Exception("Package not found")


@click.group()
def _byht():
    """Byht manager."""


@_byht.command()
def me():
    """Initialize byht"""
    for byht_dir in [BYHT_DIR, BYHT_DIR_BIN, BYHT_DIR_CACHE, BYHT_DIR_COMMANDS]:
        if not os.path.exists(byht_dir):
            os.mkdir(byht_dir)
    byht.get_index(BYHT_REPO, no_cache=True, save_cache=True)
    click.echo("Make sure you update your .bash_profile.")
    click.echo(f"export PATH=$PATH:{BYHT_DIR_BIN}")


@_byht.command()
@click.argument("name")
def add(name):
    """Install a new byht"""
    package_path = os.path.join(BYHT_DIR_CACHE, name)
    package = byht.get_package(name)

    if os.path.exists(package_path):
        click.echo("Package already installed", err=True)
        exit(1)
    elif "repository" in package:
        git.Repo.clone_from(
            package["repository"],
            package_path
        )

    config_file = os.path.join(package_path, ".byht")
    package_config = {}
    venv_path = None

    if os.path.exists(config_file):
        package_config = yaml.load(open(config_file, 'r'), Loader=Loader)

    if "install" in package_config:
        if "virtualenv" in package_config["install"]:
            venv_path = os.path.join(package_path, package_config["install"]["virtualenv"])

            if not os.path.exists(venv_path):
                ret = subprocess.run(
                    f"virtualenv {venv_path} --python=python3",
                    shell=True)

                if ret.returncode != 0:
                    click.echo("Virtual environment creation returned non-zero code.", err=True)
                    exit(1)

        if "pip-requirements" in package_config["install"]:
            pip_path = os.path.join(venv_path, "bin", "pip")
            ret = subprocess.run(
                f"{pip_path} install -r {package_path}/{package_config['install']['pip-requirements']}",
                shell=True)
            if ret.returncode != 0:
                click.echo("Pip install returned non-zero code.", err=True)
                exit(1)

        if "sh" in package_config["install"]:
            ret = subprocess.run(package_config["install"]["sh"], shell=True)
            if ret.returncode != 0:
                click.echo("Installation returned non-zero code.", err=True)
                exit(ret.returncode)

    if "scripts" in package_config:
        for script_name, script_path in package_config["scripts"].items():
            if os.path.exists(os.path.join(BYHT_DIR_BIN, script_name)):
               continue 
            os.symlink(
                os.path.join(package_path, script_path),
                os.path.join(BYHT_DIR_BIN, script_name))


@_byht.command()
@click.argument("name")
def rm(name):
    """Remove a byht"""
    package_path = os.path.join(BYHT_DIR_CACHE, name)
    package = byht.get_package(name)

    if not os.path.exists(package_path):
        click.echo("Package not installed", err=True)
        exit(1)

    config_file = os.path.join(package_path, ".byht")

    package_config = {}
    
    if os.path.exists(config_file):
        package_config = yaml.load(open(config_file, "r"), Loader=Loader)

    if "scripts" in package_config:
        for script_name, script_path in package_config["scripts"].items():
            script_path = os.path.join(BYHT_DIR_BIN, script_name)
            if os.path.exists(script_path):
               os.remove(script_path)

    shutil.rmtree(package_path)


@_byht.command()
def update():
    """Update local cache"""
    byht.get_index(BYHT_REPO, no_cache=True)


@_byht.command()
@click.option("--no-cache", is_flag=True, default=False)
def ls(no_cache):
    """List available files"""
    index = byht.get_index(BYHT_REPO, no_cache=no_cache)

    for package in index.get("packages", []):
        print(f"{package['name']}: {package['description']}")


if __name__ == "__main__":
    _byht()
