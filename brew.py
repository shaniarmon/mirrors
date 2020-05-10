import json

def process():
    with open('f.json') as f:
        files = json.load(f)

    for f in files:
        if 'stable' not in f['bottle']:
            print(f"{f['name']} has no stable bottles")
        elif 'catalina' not in f['bottle']['stable']['files']:
            print(f"{f['name']} has no bottle for catalina")
        else:
            print(f['name'], f['bottle']['stable']['files']['catalina']['url'])
            

if __name__ == '__main__':
    process()