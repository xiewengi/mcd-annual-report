"""
麦当劳 MCP 客户端 - 封装 Streamable HTTP 协议调用
"""
import json
import urllib.request
import urllib.error
from typing import Optional


class McDormandMCPClient:
    """麦当劳 MCP Server 客户端"""
    
    def __init__(self, token: str, base_url: str = "https://mcp.mcd.cn"):
        self.token = token
        self.base_url = base_url
        self._next_id = 1
    
    def _call(self, method: str, params: dict) -> dict:
        """发送 MCP JSON-RPC 请求"""
        req_id = self._next_id
        self._next_id += 1
        
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        
        data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            self.base_url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"MCP HTTP {e.code}: {body}")
        except Exception as e:
            raise RuntimeError(f"MCP call failed: {e}")
    
    def initialize(self):
        """初始化连接"""
        return self._call("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "mcd-annual-report", "version": "1.0"}
        })
    
    def list_tools(self):
        """列出所有工具"""
        return self._call("tools/list", {})
    
    def call_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        """调用指定工具"""
        return self._call("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })
    
    # === 便捷方法 ===
    
    def get_orders(self) -> list:
        """获取历史订单列表"""
        resp = self.call_tool("order-list")
        content = resp.get("result", {}).get("content", [])
        
        # 尝试从 structuredContent 取
        sc = resp.get("result", {}).get("structuredContent")
        if sc and sc.get("success"):
            return sc.get("data", {}).get("list", [])
        
        # 回退：从 text 里解析
        for c in content:
            text = c.get("text", "")
            # 找 JSON 部分
            if "\"list\"" in text:
                start = text.find("{")
                if start >= 0:
                    try:
                        obj = json.loads(text[start:])
                        return obj.get("data", {}).get("list", [])
                    except:
                        pass
        return []
    
    def get_nutrition(self) -> list:
        """获取营养数据"""
        resp = self.call_tool("list-nutrition-foods")
        sc = resp.get("result", {}).get("structuredContent")
        if sc and sc.get("success"):
            raw = sc.get("data", "")
            return self._parse_nutrition(raw)
        
        # 回退从 text 取
        content = resp.get("result", {}).get("content", [])
        for c in content:
            text = c.get("text", "")
            if "{productName" in text:
                # 找第二个换行后的内容
                lines = text.split("\n")
                for i, line in enumerate(lines):
                    if "{productName" in line:
                        raw = "\n".join(lines[i+1:]).strip()
                        return self._parse_nutrition(raw)
        return []
    
    @staticmethod
    def _parse_nutrition(raw: str) -> list:
        """解析营养数据为结构化列表"""
        foods = []
        for line in raw.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 9:
                # 有些食物可能少一列，补 null
                parts += ["null"] * (9 - len(parts))
            
            def num(s):
                try:
                    v = s if s != "null" else ""
                    return float(v) if v else 0.0
                except:
                    return 0.0
            
            foods.append({
                "name": parts[0],
                "description": parts[1] if parts[1] != "null" else "",
                "energy_kj": num(parts[2]),
                "energy_kcal": num(parts[3]),
                "protein": num(parts[4]),
                "fat": num(parts[5]),
                "carbohydrate": num(parts[6]),
                "sodium": num(parts[7]),
                "calcium": num(parts[8]),
            })
        return foods
