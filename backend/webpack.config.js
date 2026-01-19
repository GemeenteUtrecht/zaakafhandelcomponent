const paths = require('./build/paths');
const { argv } = require('yargs');

let isProduction = process.env.NODE_ENV === 'production';
if (argv.production) {
    isProduction = true;
}

const MomentLocalesPlugin = require('moment-locales-webpack-plugin');
/**
 * Webpack configuration
 * Run using "webpack" or "gulp js"
 */
module.exports = {
    // Path to the js entry point (source).
    entry: {
        main: `${__dirname}/${paths.jsEntry}`,
        // webcomponents: __dirname + '/' + paths.jsSrcDir + 'webcomponents.js',
    },

    // Path to the (transpiled) js
    output: {
        path: `${__dirname}/${paths.jsDir}`, // directory
        filename: '[name].js', // file
    },

    // Use --production to optimize output.
    mode: isProduction ? 'production' : 'development',

    // Add babel (see .babelrc for settings)
    module: {
        rules: [
            {
                test: /\.(png)$/i,
                use: [
                    {
                        loader: 'base64-inline-loader',
                    },
                ],
            },
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader'],
            },
            {
                exclude: [
                    /node_modules/,
                    /static\/vendor/,
                ],
                loader: 'babel-loader',
                test: /.js?$/,
            },
        ],
    },

    // Use --sourcemap to generate sourcemap.
    devtool: argv.sourcemap ? 'sourcemap' : false,

    // Set which locales to keep for momentjs
    plugins: [
        new MomentLocalesPlugin({
            localesToKeep: ['nl'],
        }),
    ],
};
