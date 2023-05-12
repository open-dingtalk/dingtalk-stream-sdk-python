from setuptools import setup

setup(
    name='dingtalk-stream',
    version='0.1.0',
    description='A Python package for sending messages to DingTalk chatbot',
    url='https://github.com/open-dingtalk/dingtalk-stream-sdk-python',
    author='Ke Jie',
    author_email='jinxi.kj@alibaba-inc.com',
    license='MIT',
    packages=['dingtalk_stream'],
    install_requires=[
        'websockets>=11.0.2',
        'requests>=2.30.0',
        'urllib3>=1.26.15',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
)