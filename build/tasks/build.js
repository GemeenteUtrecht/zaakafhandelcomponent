const gulp = require('gulp');
const {js} = require('./js');
const {scss} = require('./scss');
const {leaflet} = require('./leaflet');

const build = gulp.parallel(js, scss, leaflet);

gulp.task('build', build);
exports.build = build;
