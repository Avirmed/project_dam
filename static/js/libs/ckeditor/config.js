/**
 * @license Copyright (c) 2003-2019, CKSource - Frederico Knabben. All rights reserved.
 * For licensing, see https://ckeditor.com/legal/ckeditor-oss-license
 */

CKEDITOR.editorConfig = function (config) {
    config.language = document.documentElement.lang || 'en';
    config.height = 100;

    config.filebrowserBrowseUrl = '/ck/browse/files';
    config.filebrowserUploadUrl = '/ck/upload/file';
    config.filebrowserImageBrowseUrl = '/ck/browse/images';
    config.filebrowserImageUploadUrl = '/ck/upload/image';

    config.toolbarGroups = [
        { name: 'document', groups: ['mode'] },
        { name: 'clipboard', groups: ['clipboard', 'undo'] },
        { name: 'basicstyles', groups: ['basicstyles', 'cleanup'] },
        { name: 'paragraph', groups: ['list', 'indent', 'blocks', 'align', 'paragraph'] },
        { name: 'links', groups: ['links'] },
        { name: 'insert', groups: ['insert'] },
        { name: 'styles', groups: ['styles'] },
        { name: 'colors', groups: ['colors'] },
        { name: 'tools', groups: ['tools'] },
        { name: 'others', groups: ['others'] },
    ];

    config.removeButtons = 'NewPage,Preview,Print,Save,Flash,Anchor';
};