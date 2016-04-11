# -*- coding: utf-8 -*-
import sqlite3


from src.tools.path import Path
from src import guide
from src.book import Book
from src.tools.config import Config
from src.tools.debug import Debug
from src.tools.http import Http             # 用于检查更新
from src.tools.db import DB
from login import Login
from src.read_list_parser import ReadListParser
from src.worker import worker_factory
from src.tools.type import Type


class EEBook(object):
    def __init__(self, recipe_kind='Notset', read_list='ReadList.txt', url=None):
        u"""
        配置文件使用$符区隔，同一行内的配置文件归并至一本电子书内
        :param recipe_kind:
        :param read_list_txt_file: default value: ReadList.txt
        :param url:
        :return:
        """
        self.recipe_kind = recipe_kind
        self.read_list = read_list
        self.url = url
        Debug.logger.info(u"self.recipe_kind: " + str(self.recipe_kind))
        Debug.logger.info(u"self.read_list: " + str(self.read_list))
        Debug.logger.info(u"self.url: " + str(self.url))

        Debug.logger.debug(u"recipe种类是:" + str(recipe_kind))
        Path.init_base_path(recipe_kind)        # 设置路径
        Path.init_work_directory(recipe_kind)   # 创建路径
        self.init_database()                    # 初始化数据库
        Config._load()
        return

    @staticmethod
    def init_config(recipe_kind):
        if recipe_kind == 'zhihu':      # TODO: 改掉硬编码
            login = Login(recipe_kind='zhihu')
        else:
            return
        # !!!!!发布的时候把Config.remember_account改成false!!!!!,使得第一次需要登录,之后用cookie即可
        # 登陆成功了,自动记录账户
        if Config.remember_account:
            Debug.logger.info(u'检测到有设置文件，直接使用之前的设置')
            # if raw_input():
            # login.start()
            # Config.picture_quality = guide.set_picture_quality()
            Config.picture_quality = 1
            # else:
            Http.set_cookie()   # SinaBlog, jianshu:DontNeed
        else:
            login.start()
            # Config.picture_quality = guide.set_picture_quality()
            Config.picture_quality = 1
            Config.remember_account = True

        # 储存设置
        Config._save()
        return

    def begin(self):
        u"""
        程序运行的主函数
        :return: book file 的列表
        """
        Debug.logger.debug(u"#Debug模式#: 不检查更新")
        self.init_config(recipe_kind=self.recipe_kind)
        Debug.logger.info(u"开始读取ReadList.txt的内容")
        bookfiles = []

        if self.url is not None:
            file_name = self.create_book(self.url, 1)
            bookfiles.append(file_name)
            return bookfiles

        with open(self.read_list, 'r') as read_list:
            counter = 1
            for line in read_list:
                line = line.replace(' ', '').replace('\r', '').replace('\n', '').replace('\t', '')  # 移除空白字符
                file_name = self.create_book(line, counter)
                bookfiles.append(file_name)
                counter += 1
        return bookfiles

    @staticmethod
    def create_book(command, counter):
        Path.reset_path()

        Debug.logger.info(u"开始制作第 {} 本电子书".format(counter))
        Debug.logger.info(u"对记录 {} 进行分析".format(command))
        task_package = ReadListParser.get_task(command)  # 分析命令

        if not task_package.is_work_list_empty():
            worker_factory(task_package.work_list)  # 执行抓取程序
            Debug.logger.info(u"网页信息抓取完毕")

        file_name_set = None
        if not task_package.is_book_list_empty():
            Debug.logger.info(u"开始从数据库中生成电子书")
            book = Book(task_package.book_list)
            file_name_set = book.create()

        if file_name_set is not None:
            file_name_set2list = list(file_name_set)
            file_name = '-'.join(file_name_set2list[0:3])
            return file_name
        return u"no epub file produced"

    @staticmethod
    def init_database():
        if Path.is_file(Path.db_path):
            DB.set_conn(sqlite3.connect(Path.db_path))
        else:
            DB.set_conn(sqlite3.connect(Path.db_path))
            with open(Path.sql_path) as sql_script:
                DB.cursor.executescript(sql_script.read())
            DB.commit()
