#!/usr/bin/env python
import re, json, urllib3, os, sys, glob, shutil

def get_github_release(user, name, release='latest'):
    try:
        urllib3.disable_warnings()
        user_agent = {'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.76 Safari/537.36'}
        http = urllib3.PoolManager(headers=user_agent)
        r = http.request('GET', 'https://api.github.com/repos/%s/%s/releases/%s' % ( str(user), str(name), str(release) ))
        return json.loads(r.data.decode('utf-8'))
    except Exception as e:
        print(e)
        return None

def parse_github_json(data):
    try:
        return data['tag_name'].lstrip('v')
    except Exception as e:
        print('\033[91m' + "error parsing json from github" + '\033[0m')
        return None

def print_ebuild(user, name, e_version, g_version=None):
    print('\033[93m' + "local  : %s-%s" % (name, e_version) + '\033[0m')
    if g_version:
        print( '\033[95m' + "github : %s/%s-%s" % (user, name, g_version) + '\033[0m')

def parse_ebuild_name(path):
    basename = os.path.basename(path)
    name = os.path.splitext(basename)[0]
    name = re.sub('-r[0-9]+$','', name)
    version = name[name.rindex('-')+1:]
    name = name[:name.rindex('-')]
    return name, version

def parse_ebuild_content(path):
    with open(path, 'r') as file:
        s = file.read()
        if 'github.com' in s:
            pattern = r'SRC_URI\=\"(.+)\"'
            m = re.search(pattern, s)
            if m:
                pattern = r'https?:\/\/github.com\/([a-zA-z0-9${}]+)\/([a-zA-z0-9${}]+)'
                m = re.match(pattern, m.group(1))
                if m:
                    return m.group(1), m.group(2)
    return None

def ask(prompt, error_msg = 'try again', valid=['y','n']):
        while True:
            value = input(prompt + " ")
            ret = value.strip().lower()[0]
            if ret and ret in valid:
                return ret
            else:
                print(error_msg, file=sys.stderr)

def check_ebuild(path):
    try:
        name, e_version = parse_ebuild_name(path)
        e_user, e_name = parse_ebuild_content(path)
        if e_user == "${PN}":
            e_user = name
        if e_name == "${PN}":
            e_name = name

        print('\033[93m' + "local  : %s-%s" % (e_name, e_version) + '\033[0m')
        data = get_github_release(e_user, e_name)
        g_version = parse_github_json(data)
        if g_version:
            print( '\033[95m' + "github : %s/%s-%s" % (e_user, e_name, g_version) + '\033[0m')
            if (str(e_version) < str(g_version)):
                if ask("Do you want to update this ebuild? [y/N]") == 'y':
                    print('\033[94m' + "updating ebuild ... " + e_version + " => " + g_version + '\033[0m')
                    npath = path.replace(e_version, g_version)
                    shutil.copy(path,npath)
                    if ask("Do you want do delete the old one? :O [y/N]") == 'y':
                        os.remove(path)
    except Exception as e:
        pass

if __name__ == "__main__":
    for root, path, files in os.walk('.', topdown=True, followlinks=False):
        path[:] = list(filter(lambda x: not x in [".git", "profiles", "metadata", "files", "scripts"], path))
        if path and root != ".":
            for dir in path:
                realpath = os.path.join(root, dir)
                fpath = list(filter(lambda x: not x.endswith("9999.ebuild"), glob.glob(os.path.join(realpath, "*.ebuild"))))
                if fpath:
                    for e in fpath:
                        check_ebuild(e)
