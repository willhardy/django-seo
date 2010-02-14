jQuery.noConflict();
(function($){
$(document).ready(function() {

    /* Here are our meta objects */
    meta_title = $('#id_seo-metadata-content_type-object_id-0-title')
    meta_heading = $('#id_seo-metadata-content_type-object_id-0-heading')
    meta_subheading = $('#id_seo-metadata-content_type-object_id-0-subheading')
    meta_keywords = $('#id_seo-metadata-content_type-object_id-0-keywords')
    meta_description = $('#id_seo-metadata-content_type-object_id-0-description')

    /* Find the first matching element for each of our metadata fields */
    obj_title = $("#id_meta_title, #id_page_title, #id_title, #id_heading").eq(0)
    obj_subheading = $("#id_meta_subtitle, #id_page_subtitle, #id_subtitle, #id_subheading").eq(0)
    obj_description = $("#id_meta_description, #id_summary, #id_description").eq(0)
    obj_keywords = $("#id_meta_keywords, #id_keywords, #id_tags").eq(0)

    /* Flag metadata fields as changed when changed */
    meta_title.change(function() { this._changed = true; })
    meta_heading.change(function() { this._changed = true; })
    meta_subheading.change(function() { this._changed = true; })
    meta_keywords.change(function() { this._changed = true; })
    meta_description.change(function() { this._changed = true; })

    /* Automatically populate empty, unchanged fields */
    obj_title.keyup(function() { if (!meta_title._changed) {meta_title.val($(this).val()); }})
    obj_title.keyup(function() { if (!meta_heading._changed) {meta_heading.val($(this).val()); }})
    obj_subheading.keyup(function() { if (!meta_subheading._changed) {meta_subheading.val($(this).val()); }})
    obj_description.keyup(function() { if (!meta_description._changed) {meta_description.val($(this).val()); }})
    obj_keywords.keyup(function() { if (!meta_keywords._changed) {meta_keywords.val($(this).val()); }})

});
})(jQuery);
