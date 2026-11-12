import asyncio
import os
import stat
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from agenti.molecules import api, library as library_module
from agenti.molecules.library import EngineUnavailable, Library, clean_title, format_of


def _native():
    try:
        import nuxiva_native
    except ImportError:
        return None
    return getattr(nuxiva_native, "molecule_build", None)


def peptide() -> bytes:
    rows = []
    serial = 0
    for k, residue in enumerate(("ALA", "GLY", "SER")):
        x0 = 4.31 * k
        for name, xyz, element in (("N", (x0, 0, 0), "N"), ("CA", (x0 + 1.46, 0, 0), "C"), ("C", (x0 + 2.98, 0, 0), "C"),
                                   ("O", (x0 + 2.98, -1.23, 0), "O")):
            serial += 1
            rows.append(f"ATOM  {serial:>5}  {name:<3} {residue:>3} A{k + 1:>4}    {xyz[0]:>8.3f}{xyz[1]:>8.3f}{xyz[2]:>8.3f}"
                        f"  1.00 10.00          {element:>2}")
    return ("TITLE     SYNTHETIC PEPTIDE\n" + "\n".join(rows) + "\nEND\n").encode()


class Upload:

    def __init__(self, data: bytes, size: int = 65536) -> None:
        self.data, self.size = data, size

    async def stream(self):
        for i in range(0, len(self.data), self.size):
            yield self.data[i:i + self.size]


class Temp(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(library_module, "ROOT", self.root / "molecules")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.library = Library()


class HelperTests(unittest.TestCase):

    def test_formats_and_titles(self):
        self.assertEqual(format_of("1abc.PDB"), "pdb")
        self.assertEqual(format_of("x.cif"), "cif")
        with self.assertRaises(ValueError):
            format_of("x.exe")
        self.assertEqual(clean_title("<b>Crambin</b>\n"), "b Crambin b")

    def test_ids_are_strict(self):
        for bad in ("../etc", "ABCDEF0123456789", "1234"):
            with self.assertRaises(KeyError):
                library_module.folder(bad)


class WithoutEngineTests(Temp):

    def test_upload_and_scene_need_the_engine(self):
        with mock.patch.dict(os.environ, {"NUXIVA_NATIVE": "0"}):
            with self.assertRaises(EngineUnavailable):
                self.library.add("a.pdb", peptide())
            with mock.patch.object(api, "library", self.library), self.assertRaises(HTTPException) as caught:
                asyncio.run(api.molecules_upload(Upload(peptide()), "a.pdb", "", "admin"))
        self.assertEqual(caught.exception.status_code, 503)

    def test_oversized_uploads_stop_early(self):
        with mock.patch.object(api, "MAX_BYTES", 1000), self.assertRaises(HTTPException) as caught:
            asyncio.run(api.molecules_upload(Upload(b"x" * 5000, 100), "a.pdb", "", "admin"))
        self.assertEqual(caught.exception.status_code, 413)


@unittest.skipIf(_native() is None, "nuxiva_native senza motore molecolare")
class EngineTests(Temp):

    def test_upload_stores_privately_and_builds_scenes(self):
        meta = self.library.add("pep.pdb", peptide())
        self.assertEqual((meta["atoms"], meta["residues"], meta["chains"]), (12, 3, ["A"]))
        self.assertEqual(meta["title"], "SYNTHETIC PEPTIDE")
        folder = library_module.folder(meta["id"])
        self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((folder / "source.pdb").stat().st_mode), 0o600)
        summary, packed = self.library.scene(meta["id"], "atoms", "element")
        atoms, bonds = struct.unpack_from("<II", packed)
        self.assertEqual(atoms, 12)
        self.assertGreaterEqual(bonds, 11)
        self.assertEqual(len(packed), 8 + atoms * 20 + bonds * 8)
        self.assertIs(self.library.scene(meta["id"], "atoms", "element")[1], packed)
        _, backbone = self.library.scene(meta["id"], "backbone", "secondary")
        self.assertEqual(struct.unpack_from("<II", backbone), (3, 2))
        self.assertEqual(self.library.listing()[0]["id"], meta["id"])
        self.library.remove(meta["id"])
        self.assertEqual(self.library.listing(), [])

    def test_garbage_is_refused(self):
        for name, data in (("x.pdb", b"\x00\x01binary"), ("x.pdb", b"HEADER only\n"), ("x.cif", b"data_x\nloop_\n_atom_site.id\n1\n")):
            with self.assertRaises(ValueError):
                self.library.add(name, data)
        with self.assertRaises(ValueError):
            self.library.scene("0123456789abcdef", "evil", "element")

    def test_display_scene_endpoint(self):
        meta = self.library.add("pep.pdb", peptide())
        request = mock.Mock()
        with mock.patch.object(api, "library", self.library), mock.patch.object(api, "require_display"):
            response = asyncio.run(api.molecule_scene(meta["id"], request, "atoms", "chain"))
            self.assertEqual(response.headers["x-molecule-atoms"], "12")
            with self.assertRaises(HTTPException) as caught:
                asyncio.run(api.molecule_scene("0123456789abcdef", request))
        self.assertEqual(caught.exception.status_code, 404)

    def test_engine_limits_from_python(self):
        engine = _native()
        with self.assertRaises(ValueError):
            engine(b"ATOM", "pdb", "everything", "element")
        with self.assertRaises(ValueError):
            engine(b"hello world", "auto", "atoms", "element")
