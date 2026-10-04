use url::Url;

pub fn validate(raw: &str) -> Result<String, String> {
    if raw.len() > 2048
        || raw.chars().any(|c| c.is_control() || c.is_whitespace())
        || raw.contains('\\')
    {
        return Err("Use a plain HTTPS link without spaces or control characters.".into());
    }
    let u = Url::parse(raw).map_err(|_| "Enter a valid HTTPS link.".to_string())?;
    if u.scheme() != "https" || u.host_str() != Some("chatgpt.com") || u.port().is_some() {
        return Err("Only HTTPS links on chatgpt.com with the standard port are allowed.".into());
    }
    if !u.username().is_empty()
        || u.password().is_some()
        || u.query().is_some()
        || u.fragment().is_some()
    {
        return Err("Remove credentials, query parameters and fragments from the link.".into());
    }
    // A launcher accepts a copied, locally tested path, without guessing dot routes.
    let p = u.path().to_ascii_lowercase();
    if [
        ".exe", ".msi", ".bat", ".cmd", ".ps1", ".sh", ".scr", ".com", ".app", ".dmg", ".pkg",
        ".jar", ".vbs",
    ]
    .iter()
    .any(|ext| p.trim_end_matches('/').ends_with(ext))
    {
        return Err("Executable or installer links are not conversation destinations.".into());
    }
    if p == "/"
        || p.split('/')
            .any(|s| matches!(s, "share" | "auth" | "api" | "backend-api" | "login"))
        || p.contains('%')
    {
        return Err(
            "Use your private conversation link; shared, login and API links are not destinations."
                .into(),
        );
    }
    Ok(u.into())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn accepts_a_user_supplied_path_without_claiming_dot_identity() {
        assert!(validate("https://chatgpt.com/c/synthetic-test").is_ok());
    }
    #[test]
    fn rejects_unsafe_and_credential_urls() {
        for u in [
            "javascript:alert(1)",
            "file:///app.exe",
            "https://chatgpt.com/files/unsafe.exe",
            "https://chatgpt.com.evil.test/c/a",
            "https://user:pass@chatgpt.com/c/a",
            "https://chatgpt.com/c/a?token=secret",
            "https://chatgpt.com/c/a#token",
            "https://chatgpt.com/share/a",
            "https://chatgpt.com/",
            "https://chatgpt.com:444/c/a",
            "https://chatgpt.com/api/a",
            "https://chatgpt.com/c/%0a",
            "https://chatgpt.com/c/a\n",
            "https://chatgpt.com\\@evil.test/c/a",
        ] {
            assert!(validate(u).is_err(), "accepted unsafe fixture");
        }
    }
}
