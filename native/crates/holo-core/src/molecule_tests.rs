#![allow(
    clippy::indexing_slicing,
    clippy::arithmetic_side_effects,
    clippy::cast_precision_loss
)]

use serde_json::Value;

use crate::HoloError;
use crate::molecule::{MAX_RESIDUES, generate, pdb_parts, sdf_parts};

const WATER: &str = "962\n  -OEChem-\n\n  3  2  0     0  0  0  0  0  0999 V2000\n    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n    0.2774    0.8929    0.2544 H   0  0  0  0  0  0  0  0  0  0  0  0\n    0.6068   -0.2383   -0.7169 H   0  0  0  0  0  0  0  0  0  0  0  0\n  1  2  1  0  0  0  0\n  1  3  1  0  0  0  0\nM  END\n$$$$\n";

fn ca(serial: usize, chain: char, x: f32) -> String {
    format!(
        "ATOM  {serial:>5}  CA  ALA {chain}{serial:>4}    {x:>8.3}{:>8.3}{:>8.3}  1.00  0.00           C",
        0.0, 0.0
    )
}

#[test]
fn sdf_keeps_real_atoms_and_bonds() {
    let parts = sdf_parts(WATER).unwrap_or_default();
    assert_eq!(parts.len(), 5);
    let names: Vec<&str> = parts.iter().filter_map(|p| p["name"].as_str()).collect();
    assert_eq!(names, vec!["bond", "bond", "atom_O", "atom_H", "atom_H"]);
    assert_eq!(parts[2]["color"], "#ff3b3b");
    let scene: Value = serde_json::from_str(&generate("sdf", WATER, "Acqua").unwrap_or_default())
        .unwrap_or(Value::Null);
    assert_eq!(scene["title"], "Acqua");
    assert_eq!(scene["parts"].as_array().map(Vec::len), Some(5));
}

#[test]
fn hostile_sdf_is_rejected() {
    assert_eq!(
        sdf_parts("x\ny\nz\n999999  0 V2000\n"),
        Err(HoloError::BadModel)
    );
    assert_eq!(
        sdf_parts("x\ny\nz\n  3  2  0 V3000\n"),
        Err(HoloError::BadModel)
    );
    let broken = WATER.replace("  1  3  1", "  1  9  1");
    assert_eq!(sdf_parts(&broken), Err(HoloError::BadModel));
    let nan = WATER.replace("    0.2774", "       NaN");
    assert_eq!(sdf_parts(&nan), Err(HoloError::BadModel));
    assert_eq!(generate("exe", WATER, "x"), Err(HoloError::BadModel));
}

#[test]
fn pdb_traces_chains_and_breaks_between_them() {
    let mut text = String::new();
    for i in 1..=4 {
        text.push_str(&ca(i, 'A', i as f32 * 3.8));
        text.push('\n');
    }
    for i in 5..=6 {
        text.push_str(&ca(i, 'B', i as f32 * 3.8));
        text.push('\n');
    }
    text.push_str("ENDMDL\n");
    text.push_str(&ca(9, 'C', 0.0));
    let parts = pdb_parts(&text).unwrap_or_default();
    let rods = parts.iter().filter(|p| p["shape"] == "cylinder").count();
    let balls = parts.iter().filter(|p| p["shape"] == "sphere").count();
    assert_eq!((balls, rods), (6, 4));
    assert!(parts.iter().all(|p| p["name"] != "protein_chain_C"));
    assert_ne!(
        parts[0]["color"],
        parts.last().map_or(Value::Null, |p| p["color"].clone())
    );
}

#[test]
fn large_proteins_are_sampled_within_limits() {
    let text: String = (1..=1000)
        .map(|i| ca(i % 9999, 'A', (i % 200) as f32 * 3.8) + "\n")
        .collect();
    let parts = pdb_parts(&text).unwrap_or_default();
    let balls = parts.iter().filter(|p| p["shape"] == "sphere").count();
    assert!(
        (MAX_RESIDUES / 2..=MAX_RESIDUES).contains(&balls),
        "{balls}"
    );
    assert!(generate("pdb", &text, "Proteina").is_ok());
}
