simulation.exe 使用说明
========================

`simulation.exe` 用于在仿真环境中执行原本在命令行中运行的脚本命令。

基本用法
--------

```bash
simulation.exe <执行脚本的命令>
```

其中，`<执行脚本的命令>` 就是你原来在终端里输入的那条命令。

示例：执行 `main.py`
----------------------

如果你平时直接在命令行中运行脚本的命令是：

```bash
python main.py
```

那么使用仿真环境时，只需要在前面加上 `simulation.exe`：

```bash
simulation.exe python main.py
```

带参数的示例
--------------

如果原来的命令是：

```bash
python main.py --config config.json --mode test
```

则使用 `simulation.exe` 时写成：

```bash
simulation.exe python main.py --config config.json --mode test
```

一般规则
--------

- 原本在命令行中怎样写脚本命令，就怎样写在 `simulation.exe` 后面。
- 不需要修改脚本内容，只是把执行方式从 `python main.py ...` 改为 `simulation.exe python main.py ...`。
- 其它解释器或工具（如 `python3`、`pipenv run python` 等）同理，在前面加上 `simulation.exe` 即可。
