"""平台适配器：把不同 IM 平台的数据，统一成同一套结构。

加一个新平台，只需要在 adapters/ 下写一个文件，实现 list_chats()，
如果该平台能读历史消息，再实现 fetch_messages()。
"""

from adapters.base import Adapter, pick_list  # noqa: F401
