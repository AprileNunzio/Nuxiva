use nuxiva_display_planner::Category;

pub const URGENT: u8 = 2;

#[must_use]
pub const fn learnable(category: Category, urgency: u8) -> bool {
    !matches!(category, Category::Safety) && urgency < URGENT
}

#[must_use]
pub const fn explorable(category: Category) -> bool {
    matches!(
        category,
        Category::Info | Category::Ambient | Category::System | Category::Media
    )
}
