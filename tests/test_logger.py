import logging

from pytchat.config.mylogger import get_logger


def test_get_logger_debug_mode_writes_detailed_logs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    logger = get_logger('test_logger_debug', logging.DEBUG)
    logger.debug('very detailed debug message')

    log_file = tmp_path / 'log.txt'
    assert log_file.exists()
    assert 'very detailed debug message' in log_file.read_text(encoding='utf-8')
    assert len([handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)]) == 1
    assert len([handler for handler in logger.handlers if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler)]) == 1

    logger2 = get_logger('test_logger_debug', logging.DEBUG)
    assert logger is logger2
    assert len([handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)]) == 1
