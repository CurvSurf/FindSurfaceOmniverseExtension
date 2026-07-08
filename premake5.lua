local ext = get_current_extension_info()

project_ext(ext)

repo_build.prebuild_link {
    { "config", ext.target_dir.."/config" },
    { "data", ext.target_dir.."/data" },
    { "findsurface", ext.target_dir.."/findsurface" },
}

repo_build.prebuild_copy {
    { "THIRD_PARTY_NOTICES.md", ext.target_dir.."/THIRD_PARTY_NOTICES.md" },
}
