const BYTES_PER_CHUNK = 1024 * 1024 * 5;
const FILE_MAX_SIZE = 1024 * 1024 * 1024 * 10;

class FileUploader {
    constructor(fileSelector, url, fileUploadDone) {
        this.fileSelector = fileSelector;
        this.url = url;
        this.fileUploadEvent = fileUploadDone;
        this.Files = [];
        this.isDone = false;
        this.doneCount = 0;
        this.targetId = null;

        var _FileUploader_ = this;
        var fileCounter = 0;
        $(this.fileSelector).each(function () {
            for (var i = 0; i < $(this)[0].files.length; i++) {
                if ($(this)[0].files[i].size <= FILE_MAX_SIZE) {
                    _FileUploader_.Files.push({
                        el: $(this),
                        file: $(this)[0].files[i],
                        part: 1,
                        start: 0,
                        end: BYTES_PER_CHUNK,
                        time: new Date().getTime() + "_" + fileCounter,
                        percent: 0,
                        statusOk: true
                    });
                } else {
                    $(this).val('');
                    toastr.error(LOCAL_VARIABLES.StaticText.Messages.FileSizeExceeded, LOCAL_VARIABLES.StaticText.Messages.Title);
                }
            }
            if ($(this)[0].file !== undefined && $(this)[0].file != '') {
                if ($(this)[0].file.size <= FILE_MAX_SIZE) {
                    _FileUploader_.Files.push({
                        el: $(this),
                        file: $(this)[0].file,
                        part: 1,
                        start: 0,
                        end: BYTES_PER_CHUNK,
                        time: new Date().getTime() + "_" + fileCounter,
                        percent: 0,
                        statusOk: true
                    });
                } else {
                    toastr.error(LOCAL_VARIABLES.StaticText.Messages.FileSizeExceeded, LOCAL_VARIABLES.StaticText.Messages.Title);
                }
                $(this)[0].file = '';
            }
            fileCounter++;
        });

        $(this.fileSelector).val('');
    }

    upload() {
        if (this.Files.length > 0) {
            $.post("/main/cleartmp");
            for (var i = 0; i < this.Files.length; i++) {
                this.sliceUpload(i);
            }
            return true;
        }
        return false;
    }

    sliceUpload(fileIndex) {
        var formData = new FormData();
        var slice = (this.Files[fileIndex].file.slice ? 'slice' : (this.Files[fileIndex].file.mozSlice ? 'mozSlice' : (this.Files[fileIndex].file.webkitSlice ? 'webkitSlice' : 'slice')));

        formData.append('file', this.Files[fileIndex].file[slice](this.Files[fileIndex].start, this.Files[fileIndex].end));
        formData.append('filename', this.Files[fileIndex].file.name);
        formData.append('part', this.Files[fileIndex].part);
        formData.append('time', this.Files[fileIndex].time);
        if (this.Files[fileIndex].file.size <= this.Files[fileIndex].end) {
            formData.append('lastPart', true);
            formData.append('contentid', this.targetId);
        }

        var request = new XMLHttpRequest();
        var _FileUploader_ = this;

        request.addEventListener('readystatechange', function () {
            if (this.readyState == 4 && this.status == 200) {
                if (_FileUploader_.Files[fileIndex].part == 1) {
                    if (this.responseText == '') {
                        _FileUploader_.Files[fileIndex].statusOk = false;
                    } else {
                        _FileUploader_.Files[fileIndex].tmpFileName = this.responseText;
                    }
                }
                if (_FileUploader_.Files[fileIndex].end < _FileUploader_.Files[fileIndex].file.size) {
                    _FileUploader_.Files[fileIndex].start = _FileUploader_.Files[fileIndex].end;
                    _FileUploader_.Files[fileIndex].end += BYTES_PER_CHUNK;
                    if (_FileUploader_.Files[fileIndex].file.size < _FileUploader_.Files[fileIndex].end) {
                        _FileUploader_.Files[fileIndex].end = _FileUploader_.Files[fileIndex].file.size;
                    }
                    _FileUploader_.Files[fileIndex].part++;
                    _FileUploader_.Files[fileIndex].percent = Math.ceil(_FileUploader_.Files[fileIndex].end * 99.0 / _FileUploader_.Files[fileIndex].file.size);
                    _FileUploader_.fileUploadEvent(_FileUploader_.Files[fileIndex], _FileUploader_.isDone);
                    if (_FileUploader_.Files[fileIndex].statusOk) {
                        _FileUploader_.sliceUpload(fileIndex);
                    }
                } else {
                    _FileUploader_.Files[fileIndex].percent = 100;
                    _FileUploader_.Files[fileIndex].jsonData = JSON.parse(this.responseText);
                    _FileUploader_.fileUploadEvent(_FileUploader_.Files[fileIndex], _FileUploader_.isDone);
                    _FileUploader_.doneCount++;
                }
            }
        });

        request.addEventListener('error', function () {
            toastr.error(LOCAL_VARIABLES.StaticText.Messages.FileUploadError, LOCAL_VARIABLES.StaticText.Messages.Title);
        });

        request.addEventListener('load', function () {
            if (_FileUploader_.doneCount == _FileUploader_.Files.length) {
                _FileUploader_.isDone = true;
                _FileUploader_.fileUploadEvent(_FileUploader_.Files[0], _FileUploader_.isDone);
            }
        });

        request.open("post", this.url);
        request.send(formData);
    }
}