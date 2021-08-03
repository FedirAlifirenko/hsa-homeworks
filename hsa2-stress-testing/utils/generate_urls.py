import argparse
import random
random.seed(123)


class BasePath:

    _url = 'http://localhost:8000'

    def __init__(self, data):
        self._data = data

    @property
    def value(self):
        return self._data

    def __call__(self, *args, **kwargs):
        return self._url + self.value


class RandomIntPath(BasePath):

    @property
    def value(self):
        return self._data.format(int=random.randint(1, 100))


PATHS = [
    BasePath('/items-count'),
    RandomIntPath('/items?price_gt={int}'),
    RandomIntPath('/items/{int}'),
]


def main(urls_num: int):
    urls = [random.choice(PATHS)() + '\n' for _ in range(urls_num)]
    with open('urls.txt', 'w') as fp:
        fp.writelines(urls)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('urls_num', type=int)
    args = parser.parse_args()

    main(args.urls_num)
