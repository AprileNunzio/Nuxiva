use crate::{IntentError, Outcome, StrictReply};

type Check = Result<(), IntentError>;

fn answer(value: &str) -> Outcome {
    Outcome::Answer(value.to_owned())
}

#[test]
fn computes_products_sums_and_differences() -> Check {
    let strict = StrictReply::new()?;
    let product = "quanto fa 12 per 12? rispondi solo con il numero";
    assert_eq!(strict.deterministic(product), answer("144"));
    assert_eq!(
        strict.deterministic("What is -3 + 10? reply with only the number."),
        answer("7")
    );
    assert_eq!(
        strict.deterministic("quanto fa 5 − 9? rispondi solo con il numero"),
        answer("-4")
    );
    Ok(())
}

#[test]
fn large_products_do_not_overflow() -> Check {
    let strict = StrictReply::new()?;
    let text = "quanto fa 999999999999 per 999999999999? rispondi solo con il numero";
    assert_eq!(
        strict.deterministic(text),
        answer("999999999998000000000001")
    );
    Ok(())
}

#[test]
fn sorts_alphabetically_with_folding() -> Check {
    let strict = StrictReply::new()?;
    assert_eq!(
        strict.deterministic("ordina in ordine alfabetico: pera, Mela, banana."),
        answer("banana, Mela, pera")
    );
    assert_eq!(
        strict.deterministic("sort alphabetically: zebra, Äpfel, apple"),
        answer("apple, Äpfel, zebra")
    );
    Ok(())
}

#[test]
fn rejects_what_is_not_a_plain_list() -> Check {
    let strict = StrictReply::new()?;
    assert_eq!(
        strict.deterministic("ordina alfabeticamente: solo"),
        Outcome::NoAnswer
    );
    assert_eq!(
        strict.deterministic("ordina alfabeticamente: a1, b"),
        Outcome::NoAnswer
    );
    assert_eq!(strict.deterministic("ciao"), Outcome::NoAnswer);
    Ok(())
}

#[test]
fn exotic_input_is_deferred() -> Check {
    let strict = StrictReply::new()?;
    assert_eq!(
        strict.deterministic("ordina alfabeticamente: αβγ, δ"),
        Outcome::Defer
    );
    assert_eq!(
        strict.deterministic("\u{1c}ordina alfabeticamente: a, b"),
        Outcome::Defer
    );
    assert_eq!(
        strict.deterministic("quanto fa ٣ per 4? rispondi solo con il numero"),
        Outcome::Defer
    );
    Ok(())
}
