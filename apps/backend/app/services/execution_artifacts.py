"""Confined local files and integrity metadata shared by worker and API."""
import hashlib
import os
from pathlib import Path
import re
import stat


def artifact_path(root, execution_id, item_id, filename):
    if (not isinstance(filename, str) or not filename or len(filename) > 512
            or any(c in filename for c in '/\\:<>"|?*')
            or any(ord(c) < 32 for c in filename) or filename.endswith((' ', '.'))
            or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', filename, re.I)):
        raise RuntimeError('ARTIFACT_UNAVAILABLE')
    root = Path(os.path.abspath(root))
    path = root / str(execution_id) / str(item_id) / filename
    # Reject reparse points, including Windows junctions, on every managed component.
    for component in [root, root / str(execution_id), path.parent, path]:
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise RuntimeError('ARTIFACT_UNAVAILABLE')
    if path.resolve().parent != (root.resolve() / str(execution_id) / str(item_id)):
        raise RuntimeError('ARTIFACT_UNAVAILABLE')
    return path


def open_artifact(root, execution_id, item_id, filename, *, size=None, checksum=None):
    """Return the same handle used for validation; the caller must close it."""
    handle = None
    try:
        path = artifact_path(root, execution_id, item_id, filename)
        before = path.stat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise RuntimeError('ARTIFACT_UNAVAILABLE')
        handle = path.open('rb')
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino):
            raise RuntimeError('ARTIFACT_UNAVAILABLE')
        # Recheck managed components after opening and use no later path-based open.
        artifact_path(root, execution_id, item_id, filename)
        digest = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
        actual_checksum = digest.hexdigest()
        after = os.fstat(handle.fileno())
        if (info.st_size, info.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError('ARTIFACT_UNAVAILABLE')
        if size is not None and info.st_size != size:
            raise RuntimeError('ARTIFACT_UNAVAILABLE')
        if checksum is not None and actual_checksum != checksum:
            raise RuntimeError('ARTIFACT_UNAVAILABLE')
        handle.seek(0)
        return handle, info.st_size, actual_checksum
    except (OSError, ValueError, RuntimeError):
        if handle is not None:
            handle.close()
        raise RuntimeError('ARTIFACT_UNAVAILABLE') from None


def collect_artifacts(entries, root, execution_id, item_id):
    # Normalize dot segments without resolving away links before containment checks.
    validated, downloaded = {}, set()
    for entry in entries:
        if entry.get('type') not in {'download', 'validated_file'}:
            continue
        path = os.path.abspath(entry['path'])
        if entry['type'] == 'download':
            downloaded.add(path)
            validated.pop(path, None)
        else:
            validated[path] = entry
    if not downloaded.issubset(validated):
        raise RuntimeError('ARTIFACT_NOT_VALIDATED')
    records = []
    for raw_path, entry in validated.items():
        path = Path(raw_path)
        try:
            expected = artifact_path(root, execution_id, item_id, path.name)
            if path != expected:
                raise RuntimeError('ARTIFACT_UNAVAILABLE')
            handle, size, checksum = open_artifact(root, execution_id, item_id, path.name,
                                                    size=entry.get('size'), checksum=entry.get('checksum'))
        except (OSError, ValueError):
            raise RuntimeError('ARTIFACT_UNAVAILABLE') from None
        handle.close()
        records.append(dict(type='VALIDATED_FILE', filename=path.name,
                            local_path=str(path), size=size, checksum=checksum))
    return records
