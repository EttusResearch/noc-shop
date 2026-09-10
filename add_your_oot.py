#!/usr/bin/env python3
"""Interactively create a new site_gen/sources/*.yml entry for the Noc Shop.

See source/add_your_oot.md for the full instructions on how to add your
RFNoC out-of-tree module to the Noc Shop.
"""

import argparse
import os
import re
import subprocess
import sys

SOURCES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site_gen', 'sources')


def repo_name_from_url(url):
    """Derive a repository name (without .git) from a git URL."""
    name = url.rstrip('/')
    if name.endswith('.git'):
        name = name[:-len('.git')]
    return os.path.basename(name)


def github_https_url(source_url):
    """Try to derive a github.com https URL from a git source URL.

    Handles the common forms:
    - https://github.com/OWNER/REPO.git
    - git@github.com:OWNER/REPO.git
    Returns None if the source URL isn't a recognizable GitHub URL.
    """
    url = source_url.strip()
    if url.endswith('.git'):
        url = url[:-len('.git')]

    match = re.match(r'^git@github\.com:(?P<path>.+)$', url)
    if match:
        return f"https://github.com/{match.group('path')}"

    match = re.match(r'^https?://github\.com/(?P<path>.+)$', url)
    if match:
        return f"https://github.com/{match.group('path')}"

    return None


def get_current_git_branch():
    """Return the current git branch name of this checkout, or None."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def prompt(question, default=None):
    """Ask the user a question, optionally with a default value."""
    if default:
        answer = input(f"{question} [{default}]: ").strip()
        return answer or default
    return input(f"{question}: ").strip()


def prompt_yes_no(question, default=True):
    """Ask a yes/no question, returning True/False."""
    suffix = 'Y/n' if default else 'y/N'
    answer = input(f"{question} [{suffix}]: ").strip().lower()
    if not answer:
        return default
    return answer in ('y', 'yes')


def parse_args():
    parser = argparse.ArgumentParser(
        description='Create a new Noc Shop entry for your RFNoC OOT module.',
    )
    parser.add_argument('--source', help='Git clone URL of your repository, e.g., https://github.com/OWNER/REPO.git')
    parser.add_argument('--gitbranch', help='Git branch to use (default: main)')
    parser.add_argument('--title', help='Full display title of your OOT module')
    parser.add_argument('--short-title', dest='short_title', help='Short title / identifier (default: repository name)')
    parser.add_argument('--url', help='Website URL for your repository (default: derived GitHub URL)')
    return parser.parse_args()


def gather_info(args):
    """Interactively collect (or use provided) values for the new entry."""
    source = args.source or prompt('Git clone URL of your repository (e.g., https://github.com/OWNER/REPO.git)')
    while not source:
        print('A source URL is required.')
        source = prompt('Git clone URL of your repository')

    default_short_title = repo_name_from_url(source)
    default_url = github_https_url(source) or source

    gitbranch = args.gitbranch or prompt('Git branch', default='main')
    title = args.title or prompt('Title of your OOT module', default=default_short_title)
    short_title = args.short_title or prompt('Short title', default=default_short_title)
    url = args.url or prompt('Website URL', default=default_url)

    return {
        'source': source,
        'gitbranch': gitbranch,
        'title': title,
        'short_title': short_title,
        'url': url,
    }


def run_git_command(cmd):
    """Ask for confirmation, then run a single git command if approved."""
    if not prompt_yes_no(f"Run '{' '.join(cmd)}'?", default=True):
        print('Skipped.')
        return False
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f'Command failed with exit code {result.returncode}.')
        return False
    return True


def check_branch_warning():
    """Warn the user if they are currently on the main branch, offer to check out a new one.

    Returns True if a new branch was checked out, False if it was offered but
    skipped/failed, or None if the check didn't apply (not on main).
    """
    branch = get_current_git_branch()
    if branch != 'main':
        return None
    print()
    print("You are currently on the 'main' branch of the Noc Shop repository.")
    print('It is recommended to create a new branch before submitting a pull request.')
    new_branch = prompt('New branch name', default='my_oot_module')
    checked_out = run_git_command(['git', 'checkout', '-b', new_branch])
    print()
    return checked_out


def run_git_commands(out_path, short_title):
    """Run git add/commit/push for the new source file, confirming each command.

    Returns a dict {'add': bool, 'commit': bool, 'push': bool} with the outcome
    of each step. Steps after a failed/skipped one are not attempted.
    """
    branch = get_current_git_branch() or '<your-branch-name>'
    commit_message = prompt('Commit message', default=f'Add {short_title} to the Noc Shop')

    status = {'add': False, 'commit': False, 'push': False}

    status['add'] = run_git_command(['git', 'add', out_path])
    if not status['add']:
        return status

    status['commit'] = run_git_command(['git', 'commit', '-m', commit_message])
    if not status['commit']:
        return status

    status['push'] = run_git_command(['git', 'push', '-u', 'origin', branch])
    return status


def render_yaml(info):
    """Render the collected info as YAML text, in a fixed field order."""
    lines = [
        f"source: {info['source']}",
        f"gitbranch: {info['gitbranch']}",
        f"title: {info['title']}",
        f"short_title: {info['short_title']}",
        f"url: {info['url']}",
    ]
    return '\n'.join(lines) + '\n'


def status_marker(done):
    """Return a green checkmark or a 'missing' marker for use in a step list."""
    return '\033[92m\u2713\033[0m' if done else '\033[91m\u2717 (missing)\033[0m'


def print_next_steps(out_path, short_title, checked_out_branch, git_status):
    """Print the pull-request checklist, marking completed steps with a checkmark."""
    print('\nNext steps to open a pull request:')
    if checked_out_branch is not None:
        print(f'  {status_marker(checked_out_branch)} Check out a new branch')
    print(f"  {status_marker(git_status['add'])} git add {out_path}")
    print(f"  {status_marker(git_status['commit'])} git commit -m \"Add {short_title} to the Noc Shop\"")
    print(f"  {status_marker(git_status['push'])} git push -u origin <your-branch-name>")
    print(f'  {status_marker(False)} Open a pull request against https://github.com/EttusResearch/noc-shop')


def main():
    args = parse_args()

    checked_out_branch = check_branch_warning()

    info = gather_info(args)
    yaml_text = render_yaml(info)

    os.makedirs(SOURCES_DIR, exist_ok=True)
    out_path = os.path.join(SOURCES_DIR, f"{info['short_title']}.yml")

    with open(out_path, 'w') as f:
        f.write(yaml_text)

    while True:
        print(f"\nWrote {out_path}:\n")
        print(yaml_text)

        if prompt_yes_no('Does this look correct?', default=True):
            git_status = run_git_commands(out_path, info['short_title'])
            print_next_steps(out_path, info['short_title'], checked_out_branch, git_status)
            break

        print(f'\nPlease edit {out_path} in your editor of choice.')
        input('Press Enter once you have finished editing (or Ctrl+C to abort)... ')
        with open(out_path, 'r') as f:
            yaml_text = f.read()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nAborted.')
        sys.exit(1)
