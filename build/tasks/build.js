const gulp = require('gulp');
const {scss} = require('./scss');

const build = scss;

gulp.task('build', build);
exports.build = build;
