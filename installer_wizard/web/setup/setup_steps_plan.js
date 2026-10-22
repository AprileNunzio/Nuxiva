(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const PURPOSES = Object.freeze(["home", "security", "work", "family", "knowledge"]);

  function chosen(ctx) {
    return ctx.draft.purposes || ctx.config.purposes || [];
  }

  function answers(ctx) {
    return ctx.draft.consents || ctx.config.consents || {};
  }

  function skipped(ctx) {
    return ctx.draft.skip || ctx.config.skip || [];
  }

  function asked(ctx) {
    const catalogue = (ctx.boot.plan || {}).purposes || {};
    return [...new Set(chosen(ctx).flatMap((id) => (catalogue[id] || {}).consents || []))];
  }

  function included(ctx) {
    const catalogue = (ctx.boot.plan || {}).purposes || {};
    return [...new Set(chosen(ctx).flatMap((id) => (catalogue[id] || {}).enable || []))];
  }

  function choice(ctx, label, sub, active, onClick) {
    const button = ctx.el("button", `brain-card ${active ? "active" : ""}`.trim());
    button.type = "button";
    button.setAttribute("aria-pressed", String(active));
    button.append(ctx.el("b", "", label));
    if (sub) button.append(ctx.el("small", "", sub));
    button.addEventListener("click", onClick);
    return button;
  }

  function paintPurposes(ctx) {
    const on = chosen(ctx);
    $("purpose-grid").replaceChildren(...PURPOSES.map((id) => choice(ctx, ctx.t(`purpose-${id}`), ctx.t(`purpose-${id}-sub`), on.includes(id), () => {
      ctx.draft.purposes = on.includes(id) ? on.filter((p) => p !== id) : [...on, id];
      ctx.draft.consents = Object.fromEntries(Object.entries(answers(ctx)).filter(([key]) => asked(ctx).includes(key)));
      paintPurposes(ctx);
      ctx.refresh();
    })));
    $("purpose-none").hidden = on.length > 0;
  }

  function paintConsents(ctx) {
    const list = $("consent-list");
    const given = answers(ctx);
    list.replaceChildren(...asked(ctx).map((id) => {
      const card = ctx.el("div", "live-card consent-item");
      card.append(ctx.el("b", "", ctx.t(`consent-${id}`)), ctx.el("small", "", ctx.t(`consent-${id}-sub`)));
      const row = ctx.el("div", "brain-mode-row");
      [[true, "consent-yes"], [false, "consent-no"]].forEach(([value, key]) => {
        row.append(choice(ctx, ctx.t(key), "", given[id] === value, () => {
          ctx.draft.consents = { ...answers(ctx), [id]: value };
          paintConsents(ctx);
          ctx.refresh();
        }));
      });
      card.append(row);
      return card;
    }));
    $("consent-none").hidden = asked(ctx).length > 0;
    const features = included(ctx);
    $("feature-card").hidden = features.length === 0;
    const off = skipped(ctx);
    $("feature-grid").replaceChildren(...features.map((key) => choice(ctx, ctx.t(`feat-${key}`), "", !off.includes(key), () => {
      ctx.draft.skip = off.includes(key) ? off.filter((k) => k !== key) : [...off, key];
      paintConsents(ctx);
    })));
  }

  const step6 = {
    render(ctx) {
      paintPurposes(ctx);
    },
    collect(ctx) {
      const purposes = chosen(ctx);
      return { purposes, consents: Object.fromEntries(Object.entries(answers(ctx)).filter(([key]) => asked(ctx).includes(key))) };
    },
    checks(ctx) {
      return [{ key: "chk-purposes", ok: chosen(ctx).length > 0 ? true : null }];
    },
    analytics(ctx) {
      return [["an-purposes", chosen(ctx).length], ["an-features", included(ctx).length]];
    }
  };

  const step7 = {
    render(ctx) {
      paintConsents(ctx);
    },
    collect(ctx) {
      const given = answers(ctx);
      if (asked(ctx).some((id) => typeof given[id] !== "boolean")) throw new Error("err-consents");
      return { consents: Object.fromEntries(asked(ctx).map((id) => [id, given[id]])), skip: skipped(ctx).filter((key) => included(ctx).includes(key)) };
    },
    checks(ctx) {
      const given = answers(ctx);
      const list = asked(ctx);
      const done = list.filter((id) => typeof given[id] === "boolean").length;
      return [{ key: "chk-consents", ok: list.length === 0 ? null : done === list.length, vars: { done, total: list.length } }];
    },
    analytics(ctx) {
      const given = answers(ctx);
      const list = asked(ctx);
      return [["an-consents-yes", list.filter((id) => given[id] === true).length], ["an-consents-no", list.filter((id) => given[id] === false).length]];
    }
  };

  window.SetupPlan = Object.freeze({ chosen, answers, skipped, asked, included });
  window.SetupStepDefs = Object.assign(window.SetupStepDefs || {}, { 6: step6, 7: step7 });
})();
