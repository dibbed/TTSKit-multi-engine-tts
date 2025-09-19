#!/usr/bin/env python3
"""
Script to generate CHANGELOG.md from git commits
"""

import subprocess
import re
from datetime import datetime


def main():
    # Get git log
    result = subprocess.run(['git', 'log', '--oneline', '--since=1.week.ago'],
                          capture_output=True, text=True)

    if result.returncode == 0:
        commits = result.stdout.strip().split('\n')

        # Generate changelog
        changelog_content = '''# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- New features and improvements

### Changed
- Changes to existing functionality

### Fixed
- Bug fixes

### Removed
- Removed features

## Recent Changes

'''

        for commit in commits:
            if commit:
                # Extract commit message
                message = commit.split(' ', 1)[1] if ' ' in commit else commit

                # Categorize commit
                if message.startswith('feat:'):
                    changelog_content += f'- {message}\n'
                elif message.startswith('fix:'):
                    changelog_content += f'- {message}\n'
                elif message.startswith('docs:'):
                    changelog_content += f'- {message}\n'
                elif message.startswith('refactor:'):
                    changelog_content += f'- {message}\n'
                elif message.startswith('test:'):
                    changelog_content += f'- {message}\n'
                else:
                    changelog_content += f'- {message}\n'

        # Write CHANGELOG
        with open('CHANGELOG.md', 'w', encoding='utf-8') as f:
            f.write(changelog_content)

        print('✅ CHANGELOG updated successfully')
    else:
        print('❌ Failed to get git log')


if __name__ == '__main__':
    main()
