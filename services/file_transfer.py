"""FTP / FTPS upload with the dashboard's connection settings (Services ->
File Transfer, and the same field set on cameras' Upload JPG tab).

Settings dict keys (FTPConfigures): ServerIPAddress, Port, Timeout, Username,
Password, ConnectionModes (active|passive), TransferType (binary|ascii),
TLS (NoTLSSupport|UseExplicitTLS|UseImplicitTLS|UseRequireTLS),
DirectoryStructure (1 root | 2 parent | 3 parent/child), ParentDirectory,
ChildDirectory. Standard library only (ftplib + ssl).
"""

import ftplib
import logging
import os
import ssl

from util import util as Util

logger = logging.getLogger("worker")


class ImplicitFtpTls(ftplib.FTP_TLS):
    """FTPS over an implicitly TLS-wrapped control connection (port 990)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sock = None

    @property
    def sock(self):
        return self._sock

    @sock.setter
    def sock(self, value):
        if value is not None and not isinstance(value, ssl.SSLSocket):
            value = self.context.wrap_socket(value)
        self._sock = value


def _connect(host, cfg):
    port = Util.safe_int(cfg.get("Port"), 0)
    timeout = Util.safe_int(cfg.get("Timeout"), 30) or 30
    tls = str(cfg.get("TLS") or "NoTLSSupport")
    user = str(cfg.get("Username") or "")
    password = str(cfg.get("Password") or "")

    if tls == "UseImplicitTLS":
        ftp = ImplicitFtpTls(context=ssl.create_default_context())
        ftp.connect(host, port or 990, timeout=timeout)
        ftp.login(user, password)
        ftp.prot_p()
    elif tls in ("UseExplicitTLS", "UseRequireTLS"):
        ftp = ftplib.FTP_TLS(context=ssl.create_default_context())
        ftp.connect(host, port or 21, timeout=timeout)
        ftp.login(user, password)
        ftp.prot_p()
    else:
        ftp = ftplib.FTP()
        ftp.connect(host, port or 21, timeout=timeout)
        ftp.login(user, password)

    ftp.set_pasv(str(cfg.get("ConnectionModes") or "passive") != "active")
    return ftp


def _remote_parts(cfg):
    structure = Util.safe_int(cfg.get("DirectoryStructure"), 1)
    parts = []
    if structure >= 2 and cfg.get("ParentDirectory"):
        parts.append(str(cfg.get("ParentDirectory")).strip("/"))
    if structure >= 3 and cfg.get("ChildDirectory"):
        parts.append(str(cfg.get("ChildDirectory")).strip("/"))
    return [p for p in parts if p]


def upload_with_config(host, cfg, local_path, remote_name):
    """Upload one local file. Returns (ok, message) - never raises."""
    cfg = cfg if isinstance(cfg, dict) else {}
    host = (host or cfg.get("ServerIPAddress") or "").strip()
    if not host:
        return False, "Missing FTP host"
    if not os.path.isfile(local_path):
        return False, f"Local file not found: {os.path.basename(local_path)}"

    try:
        ftp = _connect(host, cfg)
    except Exception as e:
        return False, f"FTP connect failed: {type(e).__name__}: {e}"

    try:
        parts = _remote_parts(cfg)
        for part in parts:
            try:
                ftp.cwd(part)
            except ftplib.error_perm:
                ftp.mkd(part)
                ftp.cwd(part)

        with open(local_path, "rb") as handle:
            if str(cfg.get("TransferType") or "binary") == "ascii":
                ftp.storlines(f"STOR {remote_name}", handle)
            else:
                ftp.storbinary(f"STOR {remote_name}", handle)

        remote_path = "/".join(parts + [remote_name])
        return True, f"{host}:/{remote_path}"
    except Exception as e:
        return False, f"FTP upload failed: {type(e).__name__}: {e}"
    finally:
        try:
            ftp.quit()
        except Exception:
            try:
                ftp.close()
            except Exception:
                pass


def upload(filetransfer, local_path, remote_name):
    """Upload using a FileTransfer row (Hostname + Meta.Connection.configs)."""
    connection = (filetransfer.Meta or {}).get("Connection") or {}
    cfg = connection.get("configs") if isinstance(connection, dict) else {}
    return upload_with_config(filetransfer.Hostname, cfg or {}, local_path, remote_name)
