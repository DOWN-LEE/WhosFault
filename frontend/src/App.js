import { Route, Redirect, Switch } from 'react-router-dom';
import { ConnectedRouter } from 'connected-react-router';
import './App.css';
import React from 'react';

import Home from './Home/Home';
import Result from './Home/result';
import Riot from './Riot';

import riot from './store/riot.txt';

function App(props) {
  return (
    <ConnectedRouter history={props.history}>
      <div className="App" data-testid="App">
        <Switch>
          <Route path="/home" exact component={Home} />
          <Route path='/result/:username' exact component={Result}/>
          <Route path='/riot.txt' exact component={riot}/>
          <Redirect exact from="/" to="home" />
          <Route render={() => <h1 data-testid="NotFound">Not Found</h1>} />
        </Switch>
      </div>
    </ConnectedRouter>
  );
}

export default App;
