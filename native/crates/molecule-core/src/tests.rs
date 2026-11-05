use crate::{ColorScheme, Format, Limits, Lod, MolError, build, parse};

struct Row {
    hetero: bool,
    name: &'static str,
    residue: &'static str,
    chain: &'static str,
    seq: i32,
    xyz: [f32; 3],
    element: &'static str,
}

fn peptide() -> Vec<Row> {
    let mut rows = Vec::new();
    for ((seq, x0), residue) in (1..).zip([0.0_f32, 4.31, 8.62]).zip(["ALA", "GLY", "SER"]) {
        for (name, xyz, element) in [
            ("N", [x0, 0.0, 0.0], "N"),
            ("CA", [x0 + 1.46, 0.0, 0.0], "C"),
            ("C", [x0 + 2.98, 0.0, 0.0], "C"),
            ("O", [x0 + 2.98, -1.23, 0.0], "O"),
        ] {
            rows.push(Row {
                hetero: false,
                name,
                residue,
                chain: "A",
                seq,
                xyz,
                element,
            });
        }
    }
    rows.push(Row {
        hetero: true,
        name: "O",
        residue: "HOH",
        chain: "A",
        seq: 101,
        xyz: [30.0, 30.0, 30.0],
        element: "O",
    });
    rows
}

fn pdb(rows: &[Row]) -> String {
    let mut out = String::from(
        "HEADER    TEST\nTITLE     SYNTHETIC PEPTIDE\nHELIX    1   1 ALA A    1  GLY A    2  1                                   2\nSHEET    1   A 1 SER A   3  SER A   3  0\n",
    );
    for (i, r) in (1_usize..).zip(rows) {
        let tag = if r.hetero { "HETATM" } else { "ATOM  " };
        out.extend(std::iter::once(format!(
            "{tag}{:>5}  {:<3} {:>3} {}{:>4}    {:>8.3}{:>8.3}{:>8.3}  1.00 10.00          {:>2}\n",
            i, r.name, r.residue, r.chain, r.seq, r.xyz[0], r.xyz[1], r.xyz[2], r.element
        )));
    }
    out.push_str("END\n");
    out
}

fn cif(rows: &[Row]) -> String {
    let mut out = String::from(
        "data_TEST\n_struct.title 'SYNTHETIC PEPTIDE'\n#\nloop_\n_struct_conf.conf_type_id\n_struct_conf.beg_auth_asym_id\n_struct_conf.beg_auth_seq_id\n_struct_conf.end_auth_seq_id\nHELX_P A 1 2\n#\nloop_\n_struct_sheet_range.sheet_id\n_struct_sheet_range.beg_auth_asym_id\n_struct_sheet_range.beg_auth_seq_id\n_struct_sheet_range.end_auth_seq_id\nA A 3 3\n#\nloop_\n_atom_site.group_PDB\n_atom_site.id\n_atom_site.type_symbol\n_atom_site.label_atom_id\n_atom_site.label_alt_id\n_atom_site.auth_comp_id\n_atom_site.auth_asym_id\n_atom_site.auth_seq_id\n_atom_site.Cartn_x\n_atom_site.Cartn_y\n_atom_site.Cartn_z\n_atom_site.B_iso_or_equiv\n_atom_site.pdbx_PDB_model_num\n",
    );
    for (i, r) in (1_usize..).zip(rows) {
        let tag = if r.hetero { "HETATM" } else { "ATOM" };
        out.extend(std::iter::once(format!(
            "{tag} {} {} \"{}\" . {} {} {} {:.3} {:.3} {:.3} 10.00 1\n",
            i, r.element, r.name, r.residue, r.chain, r.seq, r.xyz[0], r.xyz[1], r.xyz[2]
        )));
    }
    out.push_str("ATOM 99 C CA . ALA A 1 0.0 0.0 0.0 10.00 2\n#\n");
    out
}

#[test]
fn pdb_and_cif_agree() {
    let rows = peptide();
    let a = parse(pdb(&rows).as_bytes(), Format::Auto, Limits::default());
    let b = parse(cif(&rows).as_bytes(), Format::Auto, Limits::default());
    assert!(a.is_ok() && b.is_ok());
    let (Ok(a), Ok(b)) = (a, b) else { return };
    assert_eq!(a.atoms, b.atoms);
    assert_eq!(a.secondary, b.secondary);
    let summary = a.summary();
    assert_eq!(summary.title, "SYNTHETIC PEPTIDE");
    assert_eq!(b.summary().title, "SYNTHETIC PEPTIDE");
    assert_eq!(
        (summary.atoms, summary.hetero_atoms, summary.residues),
        (13, 1, 3)
    );
    assert_eq!((summary.helices, summary.sheets), (1, 1));
    assert_eq!(summary.chains, vec!["A".to_owned()]);
}

#[test]
fn bonds_follow_covalent_radii() {
    let Ok(structure) = parse(pdb(&peptide()).as_bytes(), Format::Pdb, Limits::default()) else {
        unreachable!()
    };
    let built = build(&structure, Lod::Atoms, ColorScheme::Element);
    assert_eq!(built.positions.len(), 13 * 4);
    assert_eq!(built.colors.len(), 13 * 4);
    let pairs: Vec<(u32, u32)> = built
        .bonds
        .chunks(2)
        .filter_map(|c| Some((*c.first()?, *c.get(1)?)))
        .collect();
    for expected in [(0, 1), (1, 2), (2, 3), (2, 4), (4, 5), (6, 8)] {
        assert!(
            pairs.contains(&expected),
            "missing bond {expected:?} in {pairs:?}"
        );
    }
    assert!(!pairs.iter().any(|&(a, b)| a == 12 || b == 12));
    assert!(!pairs.contains(&(0, 2)));
}

#[test]
fn backbone_keeps_alpha_carbons() {
    let Ok(structure) = parse(pdb(&peptide()).as_bytes(), Format::Pdb, Limits::default()) else {
        unreachable!()
    };
    let built = build(&structure, Lod::Backbone, ColorScheme::Secondary);
    assert_eq!(built.positions.len(), 3 * 4);
    assert_eq!(built.bonds, vec![0, 1, 1, 2]);
    assert_eq!(built.colors.get(0..3), Some(&[255_u8, 92, 138][..]));
    assert_eq!(built.colors.get(8..11), Some(&[255_u8, 200, 60][..]));
}

#[test]
fn positions_are_centered() {
    let Ok(structure) = parse(pdb(&peptide()).as_bytes(), Format::Pdb, Limits::default()) else {
        unreachable!()
    };
    let built = build(&structure, Lod::Atoms, ColorScheme::Chain);
    let (mut low, mut high) = (f32::MAX, f32::MIN);
    for x in built.positions.chunks(4).filter_map(|c| c.first().copied()) {
        low = low.min(x);
        high = high.max(x);
    }
    assert!((low + high).abs() < 1e-3);
    assert!(built.summary.radius > 20.0);
}

#[test]
fn limits_are_enforced() {
    let text = pdb(&peptide());
    let tight = Limits {
        max_atoms: 5,
        ..Limits::default()
    };
    assert_eq!(
        parse(text.as_bytes(), Format::Pdb, tight),
        Err(MolError::TooManyAtoms)
    );
    let small = Limits {
        max_bytes: 10,
        ..Limits::default()
    };
    assert_eq!(
        parse(text.as_bytes(), Format::Pdb, small),
        Err(MolError::TooLarge)
    );
    let long = format!("ATOM  {}\n", "x".repeat(5000));
    assert_eq!(
        parse(long.as_bytes(), Format::Pdb, Limits::default()),
        Err(MolError::LineTooLong(1))
    );
    assert_eq!(
        parse(b"\xff\xfe", Format::Auto, Limits::default()),
        Err(MolError::NotText)
    );
    assert_eq!(
        parse(b"hello", Format::Auto, Limits::default()),
        Err(MolError::UnknownFormat)
    );
    assert_eq!(
        parse(b"HEADER x\n", Format::Auto, Limits::default()),
        Err(MolError::Empty)
    );
}

#[test]
fn bad_numbers_are_typed_errors() {
    let text = "ATOM      1  CA  ALA A   1      abc     0.000   0.000  1.00 10.00           C\n";
    assert_eq!(
        parse(text.as_bytes(), Format::Pdb, Limits::default()),
        Err(MolError::BadNumber(1))
    );
    let huge = "ATOM      1  CA  ALA A   1    1e30       0.000   0.000  1.00 10.00           C\n";
    assert!(parse(huge.as_bytes(), Format::Pdb, Limits::default()).is_err());
}

#[test]
fn alternate_locations_keep_first() {
    let text = "ATOM      1  CA AALA A   1       0.000   0.000   0.000  0.50 10.00           C\nATOM      2  CA BALA A   1       1.000   0.000   0.000  0.50 10.00           C\n";
    let parsed = parse(text.as_bytes(), Format::Pdb, Limits::default());
    assert_eq!(parsed.map(|s| s.atoms.len()), Ok(1));
}

#[test]
fn random_and_truncated_input_never_panics() {
    let mut seed: u64 = 0x9E37_79B9_7F4A_7C15;
    let mut next = || {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        seed
    };
    let alphabet = b"ATOMHETX_loopdata .'\";\n0123456789-+eE";
    for _ in 0..400 {
        let len = usize::try_from(next() % 600).unwrap_or(0);
        let bytes: Vec<u8> = (0..len)
            .map(|_| {
                *alphabet
                    .get(usize::try_from(next() % 39).unwrap_or(0))
                    .unwrap_or(&b' ')
            })
            .collect();
        let _ = parse(&bytes, Format::Auto, Limits::default());
        let _ = parse(&bytes, Format::Cif, Limits::default());
        let _ = parse(&bytes, Format::Pdb, Limits::default());
    }
    for text in [pdb(&peptide()), cif(&peptide())] {
        for cut in (0..text.len()).step_by(7) {
            let _ = parse(
                text.as_bytes().get(..cut).unwrap_or(b""),
                Format::Auto,
                Limits::default(),
            );
        }
    }
}
