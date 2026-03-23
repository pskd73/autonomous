import asyncio
import logging
import subprocess
from typing import Dict, Any, Optional

from config import Config

logger = logging.getLogger(__name__)

class BashTool:
    def __init__(self, config: Config):
        self.config = config
    
    async def execute(
        self, 
        command: str, 
        cwd: Optional[str] = None,
        timeout: int = 60
    ) -> Dict[str, Any]:
        if cwd is None:
            cwd = self.config.workspace_path
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Executing command: `{command}` in `{cwd}`")

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "output": "",
                    "error": f"Command timed out after {timeout} seconds",
                    "exit_code": -1,
                    "execution_time": timeout,
                    "command": command
                }
            
            end_time = asyncio.get_event_loop().time()
            execution_time = end_time - start_time
            
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            output = stdout_str
            if stderr_str:
                output += f"\n[stderr]\n{stderr_str}" if output else stderr_str
            
            return {
                "output": output,
                "exit_code": process.returncode,
                "execution_time": round(execution_time, 3),
                "command": command
            }
            
        except Exception as e:
            return {
                "output": "",
                "error": str(e),
                "exit_code": -1,
                "execution_time": 0,
                "command": command
            }