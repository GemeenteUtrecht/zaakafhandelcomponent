'use strict';
const gulp = require('gulp');
const gulpif = require('gulp-if');
const postcss = require('gulp-postcss');
const sourcemaps = require('gulp-sourcemaps');
const gulpSass = require('gulp-sass');
const dartSass = require('sass');
const sass = gulpSass(dartSass);
const autoprefixer = require('autoprefixer');
const cssnano = require('cssnano');
const cssbyebye = require('css-byebye');
const selectorLint = require('postcss-selector-lint');
const argv = require('yargs').argv;
const paths = require('../paths');
const { fontAwesome } = require('./font-awesome');


const isProduction = argv.production ? true : false;
const sourcemap = argv.sourcemap ? true : false;

const sassOptions = {
    outputStyle: isProduction ? 'compressed' : 'expanded',
    includePaths: [
        'node_modules/@nl-design-system'
    ],
};

let selectorLintConfig = {
    global: {
        // Simple
        type: true,
        class: true,
        id: true,
        universal: true,
        attribute: true,

        // Pseudo
        pseudo: true,
    },

    local: {
        // Simple
        type: true,
        class: true,
        id: true,
        universal: true,
        attribute: true,

        // Pseudo
        pseudo: true,
    },

    options: {
        excludedFiles: ['admin_overrides.css'],
    }
};

const _plugins = [
    autoprefixer(),
    cssbyebye({
        rulesToRemove: [
            '.btn--digid::before', // issue with background image
        ],
    }),
];

const plugins = isProduction ?
    _plugins.concat([cssnano()])
    : _plugins.concat([selectorLint(selectorLintConfig)])
;


/**
 * scss task
 * Run using "gulp scss"
 * Searches for sass files in paths.sassSrc
 * Compiles sass to css
 * Auto prefixes css
 * Optimizes css when used with --production
 * Writes css to paths.cssDir
 */
function _scss() {
    return gulp.src(paths.sassSrcDir)
        .pipe(gulpif(sourcemap, sourcemaps.init()))
        .pipe(sass(sassOptions).on("error", sass.logError))
        .pipe(postcss(plugins))
        .pipe(gulpif(sourcemap, sourcemaps.write('./')))
        .pipe(gulp.dest(paths.cssDir));
}

const scss = gulp.parallel(fontAwesome, _scss);

gulp.task('sass', scss);
gulp.task('scss', scss);
exports.scss = scss;
exports.scss = scss;
