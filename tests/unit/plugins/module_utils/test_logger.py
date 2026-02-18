#!/usr/bin/python

# Copyright 2018-2026 Fsas Technologies Inc.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""ログ機能のユニットテスト"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from unittest.mock import Mock

from ansible_collections.fsas_temp_ns.primergy.plugins.module_utils.logger import (
    AnsibleLogger,
    MockLogger,
)


class TestAnsibleLogger:
    """AnsibleLoggerクラスのテスト"""

    def test_warn_calls_module_warn(self):
        """warn()がmodule.warn()を呼ぶ"""
        mock_module = Mock()
        logger = AnsibleLogger(mock_module)

        logger.warn('test warning message')

        mock_module.warn.assert_called_once_with('test warning message')

    def test_log_calls_module_log(self):
        """log()がmodule.log()を呼ぶ"""
        mock_module = Mock()
        logger = AnsibleLogger(mock_module)

        logger.log('test log message')

        mock_module.log.assert_called_once_with('test log message')

    def test_debug_calls_module_debug(self):
        """debug()がmodule.debug()を呼ぶ"""
        mock_module = Mock()
        logger = AnsibleLogger(mock_module)

        logger.debug('test debug message')

        mock_module.debug.assert_called_once_with('test debug message')

    def test_multiple_calls(self):
        """複数回の呼び出しが正しく動作する"""
        mock_module = Mock()
        logger = AnsibleLogger(mock_module)

        logger.warn('warning 1')
        logger.log('log 1')
        logger.debug('debug 1')
        logger.warn('warning 2')

        assert mock_module.warn.call_count == 2
        assert mock_module.log.call_count == 1
        assert mock_module.debug.call_count == 1


class TestMockLogger:
    """MockLoggerクラスのテスト"""

    def test_mock_logger_records_warn(self):
        """warnメッセージが記録される"""
        logger = MockLogger()

        logger.warn('warning message')

        assert len(logger.messages['warn']) == 1
        assert logger.messages['warn'][0] == 'warning message'

    def test_mock_logger_records_log(self):
        """logメッセージが記録される"""
        logger = MockLogger()

        logger.log('log message')

        assert len(logger.messages['log']) == 1
        assert logger.messages['log'][0] == 'log message'

    def test_mock_logger_records_debug(self):
        """debugメッセージが記録される"""
        logger = MockLogger()

        logger.debug('debug message')

        assert len(logger.messages['debug']) == 1
        assert logger.messages['debug'][0] == 'debug message'

    def test_mock_logger_separate_levels(self):
        """レベルごとに別々に記録される"""
        logger = MockLogger()

        logger.warn('warning 1')
        logger.log('log 1')
        logger.debug('debug 1')
        logger.warn('warning 2')
        logger.log('log 2')

        assert len(logger.messages['warn']) == 2
        assert len(logger.messages['log']) == 2
        assert len(logger.messages['debug']) == 1
        assert logger.messages['warn'] == ['warning 1', 'warning 2']
        assert logger.messages['log'] == ['log 1', 'log 2']
        assert logger.messages['debug'] == ['debug 1']

    def test_mock_logger_initial_state(self):
        """初期状態では全てのメッセージリストが空"""
        logger = MockLogger()

        assert logger.messages['warn'] == []
        assert logger.messages['log'] == []
        assert logger.messages['debug'] == []

    def test_mock_logger_multiple_instances(self):
        """複数のインスタンスが独立して動作する"""
        logger1 = MockLogger()
        logger2 = MockLogger()

        logger1.warn('message from logger1')
        logger2.warn('message from logger2')

        assert len(logger1.messages['warn']) == 1
        assert len(logger2.messages['warn']) == 1
        assert logger1.messages['warn'][0] == 'message from logger1'
        assert logger2.messages['warn'][0] == 'message from logger2'


class TestAnsibleLoggerAccumulation:
    """AnsibleLoggerのログ蓄積機能のテストクラス"""

    def test_logger_accumulates_warn(self):
        """warnメッセージがバッファに蓄積される"""
        mock_module = Mock()
        mock_module._verbosity = 3
        logger = AnsibleLogger(mock_module)

        logger.warn('Warning 1')
        logger.warn('Warning 2')

        assert logger.logs() == ['[WARN] Warning 1', '[WARN] Warning 2']

    def test_logger_accumulates_log(self):
        """logメッセージがバッファに蓄積される"""
        mock_module = Mock()
        mock_module._verbosity = 3
        logger = AnsibleLogger(mock_module)

        logger.log('Log 1')
        logger.log('Log 2')

        assert logger.logs() == ['[LOG] Log 1', '[LOG] Log 2']

    def test_logger_accumulates_debug(self):
        """debugメッセージがバッファに蓄積される"""
        mock_module = Mock()
        mock_module._verbosity = 3
        logger = AnsibleLogger(mock_module)

        logger.debug('Debug 1')
        logger.debug('Debug 2')

        assert logger.logs() == ['[DEBUG] Debug 1', '[DEBUG] Debug 2']

    def test_logger_accumulates_mixed_levels(self):
        """異なるレベルのメッセージが時系列順に蓄積される"""
        mock_module = Mock()
        mock_module._verbosity = 3
        logger = AnsibleLogger(mock_module)

        logger.debug('Starting')
        logger.log('Processing')
        logger.warn('Warning occurred')
        logger.debug('Finished')

        assert logger.logs() == [
            '[DEBUG] Starting',
            '[LOG] Processing',
            '[WARN] Warning occurred',
            '[DEBUG] Finished',
        ]

    def test_logger_still_calls_module_methods(self):
        """バッファ蓄積後もmoduleのメソッドが呼ばれる（リアルタイム出力）"""
        mock_module = Mock()
        logger = AnsibleLogger(mock_module)

        logger.warn('test warn')
        logger.log('test log')
        logger.debug('test debug')

        mock_module.warn.assert_called_once_with('test warn')
        mock_module.log.assert_called_once_with('test log')
        mock_module.debug.assert_called_once_with('test debug')

    def test_empty_logger_returns_empty_list(self):
        """ログが蓄積されていない場合は空のリストを返す"""
        mock_module = Mock()
        mock_module._verbosity = 3
        logger = AnsibleLogger(mock_module)

        assert logger.logs() == []

    def test_logs_returns_none_when_verbosity_0(self):
        """verbosity=0の場合はlogs()がNoneを返す"""
        mock_module = Mock()
        mock_module._verbosity = 0
        logger = AnsibleLogger(mock_module)

        logger.warn('Warning')
        logger.log('Log')
        logger.debug('Debug')

        assert logger.logs() is None

    def test_logs_filtered_by_verbosity_1(self):
        """verbosity=1（-v）の場合はWARNのみ返される"""
        mock_module = Mock()
        mock_module._verbosity = 1
        logger = AnsibleLogger(mock_module)

        logger.warn('Warning 1')
        logger.log('Log 1')
        logger.debug('Debug 1')
        logger.warn('Warning 2')

        result = logger.logs()
        assert result == ['[WARN] Warning 1', '[WARN] Warning 2']

    def test_logs_filtered_by_verbosity_2(self):
        """verbosity=2（-vv）の場合はWARN+LOGが返される"""
        mock_module = Mock()
        mock_module._verbosity = 2
        logger = AnsibleLogger(mock_module)

        logger.warn('Warning 1')
        logger.log('Log 1')
        logger.debug('Debug 1')
        logger.warn('Warning 2')
        logger.log('Log 2')

        result = logger.logs()
        assert result == [
            '[WARN] Warning 1',
            '[LOG] Log 1',
            '[WARN] Warning 2',
            '[LOG] Log 2',
        ]

    def test_logs_filtered_by_verbosity_3(self):
        """verbosity=3（-vvv）の場合は全てのログが返される"""
        mock_module = Mock()
        mock_module._verbosity = 3
        logger = AnsibleLogger(mock_module)

        logger.warn('Warning 1')
        logger.log('Log 1')
        logger.debug('Debug 1')

        result = logger.logs()
        assert result == ['[WARN] Warning 1', '[LOG] Log 1', '[DEBUG] Debug 1']

    def test_logs_returns_none_when_empty_after_filter(self):
        """フィルタリング後に空の場合は空リストを返す"""
        mock_module = Mock()
        mock_module._verbosity = 1
        logger = AnsibleLogger(mock_module)

        # verbosity=1ではLOGとDEBUGはフィルタリングされる
        logger.log('Log 1')
        logger.debug('Debug 1')

        assert logger.logs() == []


class TestAnsibleLoggerToLogsDict:
    """AnsibleLoggerのto_logs_dict()メソッドのテストクラス"""

    def test_to_logs_dict_returns_empty_dict_when_verbosity_0(self):
        """verbosity=0の場合は空の辞書を返す"""
        mock_module = Mock()
        mock_module._verbosity = 0
        logger = AnsibleLogger(mock_module)

        logger.warn('Warning')

        assert logger.to_logs_dict() == {}

    def test_to_logs_dict_returns_logs_when_verbosity_1(self):
        """verbosity=1の場合は{'_logs': [...]}を返す"""
        mock_module = Mock()
        mock_module._verbosity = 1
        logger = AnsibleLogger(mock_module)

        logger.warn('Warning')

        result = logger.to_logs_dict()
        assert result == {'_logs': ['[WARN] Warning']}

    def test_to_logs_dict_returns_empty_logs_when_no_messages(self):
        """ログがない場合は{'_logs': []}を返す"""
        mock_module = Mock()
        mock_module._verbosity = 3
        logger = AnsibleLogger(mock_module)

        result = logger.to_logs_dict()
        assert result == {'_logs': []}

    def test_to_logs_dict_can_be_merged_with_dict(self):
        """辞書のマージ演算子と組み合わせて使用できる"""
        mock_module = Mock()
        mock_module._verbosity = 1
        logger = AnsibleLogger(mock_module)

        logger.warn('Warning')

        base_dict = {'changed': True, 'msg': 'Success'}
        result = base_dict | logger.to_logs_dict()

        assert result == {
            'changed': True,
            'msg': 'Success',
            '_logs': ['[WARN] Warning'],
        }

    def test_to_logs_dict_merge_with_empty_dict(self):
        """verbosity=0の場合、マージしても元の辞書が保持される"""
        mock_module = Mock()
        mock_module._verbosity = 0
        logger = AnsibleLogger(mock_module)

        logger.warn('Warning')

        base_dict = {'changed': True, 'msg': 'Success'}
        result = base_dict | logger.to_logs_dict()

        assert result == {'changed': True, 'msg': 'Success'}
        assert '_logs' not in result
